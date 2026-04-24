from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RuntimeInfo:
    key: str
    installed: bool
    version: str | None = None
    devices: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    install_hint: str | None = None
    status: str = "detected"


@dataclass
class RuntimeProfile:
    runtimes: list[RuntimeInfo]

    def to_dict(self) -> dict[str, Any]:
        return {"runtimes": [asdict(item) for item in self.runtimes]}


def scan_runtimes() -> RuntimeProfile:
    return RuntimeProfile(
        runtimes=[
            _scan_openvino(),
            _scan_onnxruntime(),
            _scan_cuda(),
            RuntimeInfo(
                key="directml",
                installed=False,
                status="planned",
                install_hint="Install onnxruntime-directml when DirectML support is needed.",
            ),
            RuntimeInfo(key="tensorrt", installed=False, status="detection-only"),
            RuntimeInfo(key="rocm", installed=False, status="planned"),
            RuntimeInfo(key="qualcomm-qnn", installed=False, status="planned"),
        ]
    )


def _scan_openvino() -> RuntimeInfo:
    try:
        import openvino as ov

        core = ov.Core()
        devices = list(core.available_devices)
        warnings: list[str] = []
        if "NPU" not in devices:
            warnings.append("OpenVINO is installed, but no NPU device is visible.")
        return RuntimeInfo(
            key="openvino",
            installed=True,
            version=getattr(ov, "__version__", None),
            devices=devices,
            warnings=warnings,
            install_hint="pip install 'accelscope[openvino]'",
        )
    except Exception as exc:
        return RuntimeInfo(
            key="openvino",
            installed=False,
            error=str(exc),
            install_hint="pip install 'accelscope[openvino]'",
        )


def _scan_onnxruntime() -> RuntimeInfo:
    try:
        import onnxruntime as ort  # type: ignore[import-not-found]

        providers = list(ort.get_available_providers())
        return RuntimeInfo(
            key="onnxruntime",
            installed=True,
            version=getattr(ort, "__version__", None),
            providers=providers,
            install_hint="pip install onnxruntime or onnxruntime-directml",
        )
    except Exception as exc:
        return RuntimeInfo(
            key="onnxruntime",
            installed=False,
            error=str(exc),
            install_hint="pip install onnxruntime or onnxruntime-directml",
        )


def _scan_cuda() -> RuntimeInfo:
    try:
        import ctypes

        ctypes.WinDLL("nvcuda.dll")
        return RuntimeInfo(
            key="cuda",
            installed=True,
            status="detection-only",
            install_hint="Install NVIDIA CUDA runtime and ONNX Runtime CUDA for inference.",
        )
    except Exception as exc:
        return RuntimeInfo(
            key="cuda",
            installed=False,
            status="detection-only",
            error=str(exc),
            install_hint="Install NVIDIA drivers/CUDA if this machine has an NVIDIA GPU.",
        )
