from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendInfo:
    key: str
    scope: str
    devices: tuple[str, ...]
    notes: str


BACKENDS: tuple[BackendInfo, ...] = (
    BackendInfo(
        key="openvino",
        scope="Cross-vendor CPU plus Intel GPU/NPU acceleration through OpenVINO plugins.",
        devices=("CPU", "GPU", "NPU", "AUTO", "MULTI", "HETERO"),
        notes="Best first backend for this laptop and for Intel AI PC demos.",
    ),
    BackendInfo(
        key="onnxruntime",
        scope="Portable ONNX inference with provider-based acceleration.",
        devices=("CPUExecutionProvider", "DmlExecutionProvider", "CUDAExecutionProvider"),
        notes="Good path for Windows DirectML, NVIDIA CUDA, and broad ONNX ecosystem support.",
    ),
    BackendInfo(
        key="directml",
        scope="Windows GPU/NPU-adjacent acceleration through DirectML where supported.",
        devices=("DML",),
        notes="Useful for vendor-neutral Windows GPU acceleration; NPU support depends on drivers/runtime.",
    ),
    BackendInfo(
        key="cuda",
        scope="NVIDIA GPU acceleration.",
        devices=("CUDA",),
        notes="Future backend for discrete NVIDIA GPUs and heavier local AI workloads.",
    ),
    BackendInfo(
        key="rocm",
        scope="AMD GPU acceleration.",
        devices=("ROCm",),
        notes="Future backend for Linux/AMD systems; Windows support varies by stack.",
    ),
)


def list_backends() -> tuple[BackendInfo, ...]:
    return BACKENDS


def get_backend(key: str) -> BackendInfo | None:
    normalized = key.strip().lower()
    for backend in BACKENDS:
        if backend.key == normalized:
            return backend
    return None
