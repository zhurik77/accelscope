from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelEntry:
    key: str
    task: str
    backend: str
    download: str | None
    recommended_devices: tuple[str, ...]
    notes: str
    example_command: str


CATALOG: tuple[ModelEntry, ...] = (
    ModelEntry(
        key="image-classification",
        task="Classify an image with a compact CNN or ViT-style model.",
        backend="openvino",
        download="omz:mobilenet-v3-small-1.0-224-tf",
        recommended_devices=("CPU", "GPU", "NPU", "AUTO"),
        notes="Good first benchmark because inputs are small and many models compile quickly.",
        example_command="accelscope compare .\\models\\classification.xml --devices CPU,GPU,NPU,AUTO",
    ),
    ModelEntry(
        key="object-detection",
        task="Detect objects in an image or webcam frame.",
        backend="openvino",
        download="omz:person-detection-retail-0013",
        recommended_devices=("GPU", "NPU", "AUTO", "CPU"),
        notes="Best visible demo for GitHub. GPU often wins throughput; NPU is interesting for efficiency.",
        example_command="accelscope models download object-detection --output-dir .\\models",
    ),
    ModelEntry(
        key="embeddings",
        task="Generate text embeddings for local RAG and semantic code search.",
        backend="openvino/onnxruntime",
        download=None,
        recommended_devices=("CPU", "GPU", "NPU", "AUTO"),
        notes="High-value developer workload. Useful even when final LLM runs locally or in the cloud.",
        example_command="accelscope compare .\\models\\embeddings.xml --devices CPU,GPU,NPU,AUTO",
    ),
    ModelEntry(
        key="ocr",
        task="Recognize text from screenshots, scans, and local documents.",
        backend="openvino/onnxruntime",
        download=None,
        recommended_devices=("GPU", "NPU", "AUTO", "CPU"),
        notes="Strong privacy story: process documents locally and export text/JSON.",
        example_command="accelscope compare .\\models\\ocr.xml --devices CPU,GPU,NPU,AUTO",
    ),
)


def list_models() -> tuple[ModelEntry, ...]:
    return CATALOG


def get_model(key: str) -> ModelEntry | None:
    normalized = key.strip().lower()
    for entry in CATALOG:
        if entry.key == normalized:
            return entry
    return None
