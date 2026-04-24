from __future__ import annotations

import platform
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

import psutil

from ai_pc_kit import __version__
from ai_pc_kit.inspectors import collect_report


@dataclass
class SystemCapability:
    os_name: str
    os_build: str | None
    windows_version: str | None
    architecture: str
    python_version: str
    accelscope_version: str
    power_mode: str | None = None
    battery_status: str | None = None


@dataclass
class CpuCapability:
    name: str | None
    vendor: str | None
    architecture: str
    physical_cores: int | None
    logical_cores: int | None
    base_mhz: int | None = None
    turbo_mhz: int | None = None
    instruction_hints: dict[str, bool | None] = field(default_factory=dict)


@dataclass
class GpuCapability:
    name: str
    vendor: str | None
    integrated: bool | None = None
    driver_version: str | None = None
    vram_mb: int | None = None
    directx_wddm: str | None = None
    explanation: str | None = None


@dataclass
class NpuCapability:
    name: str
    vendor: str | None
    device_class: str | None = None
    status: str | None = None
    driver_version: str | None = None
    device_id: str | None = None
    hardware_id: str | None = None
    explanation: str | None = None


@dataclass
class MemoryCapability:
    total_gb: float
    available_gb: float
    type: str | None = None
    speed_mhz: int | None = None
    explanation: str | None = None


@dataclass
class CapabilityProfile:
    system: SystemCapability
    cpu: CpuCapability | None
    gpus: list[GpuCapability]
    npus: list[NpuCapability]
    memory: MemoryCapability
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_capabilities() -> CapabilityProfile:
    warnings: list[str] = []
    report = collect_report()
    battery = psutil.sensors_battery()
    battery_status = None
    if battery is not None:
        source = "AC" if battery.power_plugged else "battery"
        battery_status = f"{source}, {round(battery.percent)}%"

    system_extra = _windows_system_extra()
    memory_extra = _windows_memory_extra()
    cpu_flags = _cpu_instruction_hints()

    cpu = None
    if report.cpu is not None:
        cpu = CpuCapability(
            name=report.cpu.name,
            vendor=_detect_vendor(report.cpu.name),
            architecture=platform.machine(),
            physical_cores=report.cpu.physical_cores,
            logical_cores=report.cpu.logical_cores,
            base_mhz=report.cpu.max_mhz,
            turbo_mhz=None,
            instruction_hints=cpu_flags,
        )
    else:
        warnings.append("CPU details were not available from the system inspector.")

    gpus = [
        GpuCapability(
            name=gpu.name,
            vendor=gpu.vendor,
            integrated=_integrated_gpu_hint(gpu.name),
            driver_version=gpu.driver_version,
            vram_mb=gpu.adapter_ram_mb,
            directx_wddm=None,
            explanation="Integrated/discrete is a best-effort name hint." if gpu.name else None,
        )
        for gpu in report.gpus
    ]

    npus = [
        NpuCapability(
            name=npu.name,
            vendor=npu.vendor,
            device_class=npu.device_class,
            status=npu.status,
            driver_version=None,
            device_id=npu.instance_id,
            hardware_id=npu.instance_id,
            explanation="Driver version is not reliably exposed by the current lightweight scan.",
        )
        for npu in report.npus
    ]

    if not gpus:
        warnings.append("No GPU was detected by the Windows video controller scan.")
    if not npus:
        warnings.append(
            "No NPU was detected. This can mean missing hardware, driver, or runtime visibility."
        )

    virtual_memory = psutil.virtual_memory()
    memory = MemoryCapability(
        total_gb=round(virtual_memory.total / (1024**3), 1),
        available_gb=round(virtual_memory.available / (1024**3), 1),
        type=memory_extra.get("type"),
        speed_mhz=memory_extra.get("speed_mhz"),
        explanation=memory_extra.get("explanation"),
    )

    return CapabilityProfile(
        system=SystemCapability(
            os_name=f"{platform.system()} {platform.release()}",
            os_build=system_extra.get("build"),
            windows_version=system_extra.get("caption"),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            accelscope_version=__version__,
            power_mode=system_extra.get("power_mode"),
            battery_status=battery_status,
        ),
        cpu=cpu,
        gpus=gpus,
        npus=npus,
        memory=memory,
        warnings=warnings,
    )


def _windows_system_extra() -> dict[str, str | None]:
    if platform.system() != "Windows":
        return {"build": None, "caption": None, "power_mode": None}
    data = _powershell_json(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption,BuildNumber | ConvertTo-Json"
    )
    power_mode = _powershell_text(
        "(powercfg /getactivescheme) -replace '^.*\\((.*)\\).*$','$1'"
    )
    if not isinstance(data, dict):
        return {"build": None, "caption": None, "power_mode": power_mode}
    return {
        "build": data.get("BuildNumber"),
        "caption": data.get("Caption"),
        "power_mode": power_mode,
    }


def _windows_memory_extra() -> dict[str, Any]:
    if platform.system() != "Windows":
        return {
            "type": None,
            "speed_mhz": None,
            "explanation": "Memory type/speed scan is currently Windows-first.",
        }
    data = _powershell_json(
        "Get-CimInstance Win32_PhysicalMemory | "
        "Select-Object -First 1 SMBIOSMemoryType,Speed | ConvertTo-Json"
    )
    if not isinstance(data, dict):
        return {
            "type": None,
            "speed_mhz": None,
            "explanation": "Memory type/speed was not reported by WMI.",
        }
    return {
        "type": _memory_type_name(data.get("SMBIOSMemoryType")),
        "speed_mhz": data.get("Speed"),
        "explanation": None,
    }


def _cpu_instruction_hints() -> dict[str, bool | None]:
    flags: dict[str, bool | None] = {"AVX2": None, "AVX512": None, "VNNI": None, "AMX": None}
    try:
        import cpuinfo  # type: ignore[import-not-found]

        raw_flags = {str(item).lower() for item in cpuinfo.get_cpu_info().get("flags", [])}
        flags["AVX2"] = "avx2" in raw_flags
        flags["AVX512"] = any(item.startswith("avx512") for item in raw_flags)
        flags["VNNI"] = "avx512_vnni" in raw_flags or "avx_vnni" in raw_flags
        flags["AMX"] = any(item.startswith("amx") for item in raw_flags)
    except Exception:
        pass
    return flags


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
    import json

    return json.loads(completed.stdout)


def _powershell_text(command: str) -> str | None:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    return text or None


def _detect_vendor(name: str | None) -> str | None:
    if not name:
        return None
    lowered = name.lower()
    if "intel" in lowered or "arc" in lowered or "ai boost" in lowered:
        return "Intel"
    if "nvidia" in lowered or "geforce" in lowered or "rtx" in lowered:
        return "NVIDIA"
    if "amd" in lowered or "radeon" in lowered or "ryzen ai" in lowered or "xdna" in lowered:
        return "AMD"
    if "qualcomm" in lowered or "hexagon" in lowered:
        return "Qualcomm"
    if "microsoft basic display" in lowered:
        return "Microsoft Basic Display Adapter"
    return None


def _integrated_gpu_hint(name: str | None) -> bool | None:
    if not name:
        return None
    lowered = name.lower()
    if "integrated" in lowered or "iris" in lowered or "arc(tm)" in lowered:
        return True
    if "nvidia" in lowered or "geforce" in lowered or "rtx" in lowered:
        return False
    return None


def _memory_type_name(value: Any) -> str | None:
    names = {
        26: "DDR4",
        34: "DDR5",
        35: "LPDDR5",
        36: "LPDDR5X",
    }
    try:
        return names.get(int(value))
    except (TypeError, ValueError):
        return None
