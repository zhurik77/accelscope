from __future__ import annotations

import json
import platform
import re
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

import psutil
from rich.console import Console
from rich.markup import escape
from rich.table import Table


@dataclass
class CpuInfo:
    name: str | None
    physical_cores: int | None
    logical_cores: int | None
    max_mhz: int | None


@dataclass
class GpuInfo:
    name: str
    vendor: str | None = None
    driver_version: str | None = None
    adapter_ram_mb: int | None = None


@dataclass
class NpuInfo:
    name: str
    vendor: str | None = None
    device_class: str | None = None
    status: str | None = None
    instance_id: str | None = None


@dataclass
class OpenVinoInfo:
    installed: bool
    version: str | None = None
    devices: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class AiPcReport:
    os: str
    python: str
    ram_gb: float
    cpu: CpuInfo | None = None
    gpus: list[GpuInfo] = field(default_factory=list)
    npus: list[NpuInfo] = field(default_factory=list)
    openvino: OpenVinoInfo = field(default_factory=lambda: OpenVinoInfo(installed=False))
    recommendations: list[str] = field(default_factory=list)


def collect_report(include_system: bool = True) -> AiPcReport:
    report = AiPcReport(
        os=f"{platform.system()} {platform.release()}",
        python=platform.python_version(),
        ram_gb=round(psutil.virtual_memory().total / (1024**3), 1),
        openvino=_inspect_openvino(),
    )

    if include_system and platform.system() == "Windows":
        report.cpu = _inspect_cpu_windows()
        report.gpus = _inspect_gpus_windows()
        report.npus = _inspect_npus_windows()
    elif include_system:
        report.cpu = CpuInfo(
            name=platform.processor() or None,
            physical_cores=psutil.cpu_count(logical=False),
            logical_cores=psutil.cpu_count(logical=True),
            max_mhz=None,
        )

    report.recommendations = _build_recommendations(report)
    return report


def render_report(report: AiPcReport, console: Console, json_output: bool = False) -> None:
    if json_output:
        console.print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return

    console.print("[bold]AI PC Capability Report[/bold]")
    console.print(f"OS: {report.os}")
    console.print(f"Python: {report.python}")
    console.print(f"RAM: {report.ram_gb} GB")

    if report.cpu:
        console.print(
            f"CPU: {report.cpu.name or 'unknown'} "
            f"({report.cpu.physical_cores} cores / {report.cpu.logical_cores} threads)"
        )

    _render_table(console, "GPU", [asdict(item) for item in report.gpus])
    _render_table(console, "NPU", [asdict(item) for item in report.npus])

    ov = report.openvino
    if ov.installed:
        console.print(f"OpenVINO: [green]{ov.version or 'installed'}[/green]")
        console.print("OpenVINO devices: " + (", ".join(ov.devices) or "none reported"))
    else:
        console.print("[yellow]OpenVINO: not installed[/yellow]")
        if ov.error:
            console.print(f"[dim]{ov.error}[/dim]")

    if report.recommendations:
        console.print("[bold]Recommendations[/bold]")
        for item in report.recommendations:
            console.print(f"- {escape(item)}")


def _render_table(console: Console, title: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        console.print(f"{title}: none detected")
        return

    table = Table(title=title)
    for key in rows[0]:
        table.add_column(key)
    for row in rows:
        table.add_row(*["" if value is None else str(value) for value in row.values()])
    console.print(table)


def _inspect_openvino() -> OpenVinoInfo:
    try:
        import openvino as ov

        core = ov.Core()
        return OpenVinoInfo(
            installed=True,
            version=getattr(ov, "__version__", None),
            devices=list(core.available_devices),
        )
    except Exception as exc:  # OpenVINO can fail on import when drivers are missing.
        return OpenVinoInfo(installed=False, error=str(exc))


def _inspect_cpu_windows() -> CpuInfo | None:
    data = _powershell_json(
        "Get-CimInstance Win32_Processor | "
        "Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | "
        "ConvertTo-Json"
    )
    if not isinstance(data, dict):
        return None
    return CpuInfo(
        name=data.get("Name"),
        physical_cores=data.get("NumberOfCores"),
        logical_cores=data.get("NumberOfLogicalProcessors"),
        max_mhz=data.get("MaxClockSpeed"),
    )


def _inspect_gpus_windows() -> list[GpuInfo]:
    data = _powershell_json(
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json"
    )
    rows = _as_rows(data)
    return [
        GpuInfo(
            name=str(row.get("Name")),
            vendor=_detect_vendor(row.get("Name")),
            driver_version=row.get("DriverVersion"),
            adapter_ram_mb=_bytes_to_mb(row.get("AdapterRAM")),
        )
        for row in rows
        if row.get("Name")
    ]


def _inspect_npus_windows() -> list[NpuInfo]:
    data = _powershell_json(
        "Get-PnpDevice | "
        "Where-Object { $_.FriendlyName -match 'NPU|AI Boost|Neural|VPU|Intel.*AI' "
        "-or $_.Class -eq 'ComputeAccelerator' } | "
        "Select-Object Status,Class,FriendlyName,InstanceId | ConvertTo-Json"
    )
    rows = _as_rows(data)
    filtered = [
        row
        for row in rows
        if row.get("Class") == "ComputeAccelerator" or _looks_like_npu(row.get("FriendlyName"))
    ]
    return [
        NpuInfo(
            name=str(row.get("FriendlyName")),
            vendor=_detect_vendor(row.get("FriendlyName")),
            device_class=row.get("Class"),
            status=row.get("Status"),
            instance_id=row.get("InstanceId"),
        )
        for row in filtered
        if row.get("FriendlyName")
    ]


def _powershell_json(command: str) -> Any:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return json.loads(completed.stdout)


def _as_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _bytes_to_mb(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value) // (1024 * 1024)
    except (TypeError, ValueError):
        return None


def _looks_like_npu(name: Any) -> bool:
    if not isinstance(name, str):
        return False
    return re.search(r"\b(NPU|VPU)\b|AI Boost|Neural|Intel.*AI", name, re.IGNORECASE) is not None


def _detect_vendor(name: Any) -> str | None:
    if not isinstance(name, str):
        return None
    lowered = name.lower()
    if "intel" in lowered or "arc" in lowered or "ai boost" in lowered:
        return "Intel"
    if "nvidia" in lowered or "geforce" in lowered or "rtx" in lowered or "cuda" in lowered:
        return "NVIDIA"
    if "amd" in lowered or "radeon" in lowered:
        return "AMD"
    if "qualcomm" in lowered or "hexagon" in lowered:
        return "Qualcomm"
    if "apple" in lowered or "neural engine" in lowered:
        return "Apple"
    return None


def _build_recommendations(report: AiPcReport) -> list[str]:
    recommendations: list[str] = []

    python_version = tuple(int(part) for part in report.python.split(".")[:2])
    has_gpu = bool(report.gpus)
    has_intel_gpu = any(gpu.vendor == "Intel" for gpu in report.gpus)
    has_nvidia_gpu = any(gpu.vendor == "NVIDIA" for gpu in report.gpus)
    has_amd_gpu = any(gpu.vendor == "AMD" for gpu in report.gpus)
    has_npu = any(_looks_like_npu(npu.name) for npu in report.npus)

    if has_gpu:
        recommendations.append("GPU path is available; include GPU in every benchmark comparison.")
    if has_intel_gpu:
        recommendations.append("Intel GPU detected; OpenVINO GPU is the best first acceleration path.")
    if has_nvidia_gpu:
        recommendations.append("NVIDIA GPU detected; consider ONNX Runtime CUDA or native CUDA backends.")
    if has_amd_gpu:
        recommendations.append("AMD GPU detected; consider ONNX Runtime DirectML on Windows or ROCm where supported.")

    if has_npu:
        recommendations.append("NPU path is available; test compact models and background workloads.")
    else:
        recommendations.append("No NPU detected; use CPU/GPU/AUTO paths and keep NPU as optional.")

    if not report.openvino.installed:
        if python_version >= (3, 13):
            recommendations.append(
                "Install Python 3.10-3.12 for OpenVINO runner compatibility, then install "
                "accelscope[openvino]."
            )
        else:
            recommendations.append("Install accelscope[openvino] to enable device discovery and runner commands.")
    elif report.openvino.devices:
        recommendations.append(
            "Run accelscope compare with CPU,GPU,NPU,AUTO to capture a publishable benchmark."
        )

    return recommendations
