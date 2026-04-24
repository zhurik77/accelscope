from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CompatibilityResult:
    backend: str
    device: str
    available: bool
    compile_ok: bool
    estimated_support: str
    error_message: str | None = None
    friendly_reason: str | None = None
    technical_details: str | None = None


@dataclass
class CompatibilityReport:
    model: str
    results: list[CompatibilityResult]

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "results": [asdict(item) for item in self.results]}


def check_compatibility(path: Path, devices: list[str] | None = None) -> CompatibilityReport:
    devices = devices or ["CPU", "GPU", "NPU", "AUTO"]
    results: list[CompatibilityResult] = []
    try:
        import openvino as ov
    except Exception as exc:
        return CompatibilityReport(
            model=str(path),
            results=[
                CompatibilityResult(
                    backend="openvino",
                    device=device,
                    available=False,
                    compile_ok=False,
                    estimated_support="unavailable",
                    error_message=str(exc),
                    friendly_reason="OpenVINO is not installed or failed to load.",
                )
                for device in devices
            ],
        )

    core = ov.Core()
    available_devices = set(core.available_devices)
    for device in devices:
        normalized = device.upper()
        available = normalized in available_devices or normalized == "AUTO"
        if not available:
            results.append(
                CompatibilityResult(
                    backend="openvino",
                    device=normalized,
                    available=False,
                    compile_ok=False,
                    estimated_support="unavailable",
                    friendly_reason=f"OpenVINO did not report a {normalized} device.",
                )
            )
            continue
        try:
            model = core.read_model(path)
            core.compile_model(model, normalized)
            results.append(
                CompatibilityResult(
                    backend="openvino",
                    device=normalized,
                    available=True,
                    compile_ok=True,
                    estimated_support="works",
                    friendly_reason="Model compiled successfully.",
                )
            )
        except Exception as exc:
            results.append(
                CompatibilityResult(
                    backend="openvino",
                    device=normalized,
                    available=True,
                    compile_ok=False,
                    estimated_support="fails",
                    error_message=str(exc),
                    friendly_reason=_friendly_reason(str(exc)),
                    technical_details=type(exc).__name__,
                )
            )
    return CompatibilityReport(model=str(path), results=results)


def _friendly_reason(error: str) -> str:
    lowered = error.lower()
    if "unsupported" in lowered or "not supported" in lowered:
        return "The model likely uses an operation or precision this device cannot compile."
    if "device" in lowered and "not" in lowered:
        return "The requested runtime device is not available or not initialized."
    if "reshape" in lowered or "shape" in lowered:
        return "The model may have dynamic or unsupported shapes for this device."
    return "The runtime failed to compile this model for this device."
