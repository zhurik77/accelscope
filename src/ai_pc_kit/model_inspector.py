from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TensorInfo:
    name: str
    shape: list[str]
    dtype: str | None = None


@dataclass
class TaskGuess:
    task_guess: str
    confidence: float
    signals: list[str] = field(default_factory=list)


@dataclass
class ModelInspection:
    path: str
    format: str
    exists: bool
    size_bytes: int | None = None
    opset: int | None = None
    inputs: list[TensorInfo] = field(default_factory=list)
    outputs: list[TensorInfo] = field(default_factory=list)
    node_count: int | None = None
    operator_types: dict[str, int] = field(default_factory=dict)
    initializer_precision_hints: dict[str, int] = field(default_factory=dict)
    dynamic_shape: bool | None = None
    bin_present: bool | None = None
    task: TaskGuess = field(default_factory=lambda: TaskGuess("unknown", 0.0, []))
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_model(path: Path) -> ModelInspection:
    if not path.exists():
        return ModelInspection(
            path=str(path),
            format=_format_from_path(path),
            exists=False,
            error="Model file does not exist.",
        )
    suffix = path.suffix.lower()
    if suffix == ".onnx":
        return _inspect_onnx(path)
    if suffix == ".xml":
        return _inspect_openvino_ir(path)
    return ModelInspection(
        path=str(path),
        format=_format_from_path(path),
        exists=True,
        size_bytes=path.stat().st_size,
        error=f"Unsupported model extension: {suffix or '<none>'}",
    )


def _inspect_onnx(path: Path) -> ModelInspection:
    inspection = ModelInspection(
        path=str(path),
        format="onnx",
        exists=True,
        size_bytes=path.stat().st_size,
    )
    try:
        import onnx  # type: ignore[import-not-found]
    except Exception as exc:
        inspection.error = "The onnx package is not installed. Install with: pip install onnx"
        inspection.warnings.append(str(exc))
        return inspection

    try:
        model = onnx.load(str(path), load_external_data=False)
        graph = model.graph
        inspection.opset = max((item.version for item in model.opset_import), default=None)
        inspection.inputs = [_onnx_value_info(item) for item in graph.input]
        inspection.outputs = [_onnx_value_info(item) for item in graph.output]
        inspection.node_count = len(graph.node)
        inspection.operator_types = dict(Counter(node.op_type for node in graph.node))
        inspection.initializer_precision_hints = dict(
            Counter(str(item.data_type) for item in graph.initializer)
        )
        inspection.dynamic_shape = _has_dynamic_shape(inspection.inputs + inspection.outputs)
        inspection.task = classify_task(inspection)
        return inspection
    except Exception as exc:
        inspection.error = str(exc)
        return inspection


def _inspect_openvino_ir(path: Path) -> ModelInspection:
    bin_path = path.with_suffix(".bin")
    inspection = ModelInspection(
        path=str(path),
        format="openvino-ir",
        exists=True,
        size_bytes=path.stat().st_size + (bin_path.stat().st_size if bin_path.exists() else 0),
        bin_present=bin_path.exists(),
    )
    if not bin_path.exists():
        inspection.warnings.append("OpenVINO IR .bin file was not found next to the .xml file.")
    try:
        import openvino as ov

        core = ov.Core()
        model = core.read_model(path)
        inspection.inputs = [_ov_port_info(port) for port in model.inputs]
        inspection.outputs = [_ov_port_info(port) for port in model.outputs]
        inspection.dynamic_shape = _has_dynamic_shape(inspection.inputs + inspection.outputs)
        inspection.task = classify_task(inspection)
        return inspection
    except Exception as exc:
        inspection.error = str(exc)
        return inspection


def classify_task(inspection: ModelInspection) -> TaskGuess:
    signals: list[str] = []
    operators = {key.lower() for key in inspection.operator_types}
    input_shapes = ["x".join(item.shape) for item in inspection.inputs]
    output_names = " ".join(item.name.lower() for item in inspection.outputs)

    if any("detection" in name.lower() for name in [inspection.path, output_names]):
        signals.append("model/output name contains detection")
        return TaskGuess("object-detection", 0.72, signals)
    if any("nms" in op or "nonmaxsuppression" in op for op in operators):
        signals.append("graph uses non-max suppression")
        return TaskGuess("object-detection", 0.78, signals)
    if any(shape.startswith("1x3x") for shape in input_shapes):
        signals.append(f"image-like input shape: {', '.join(input_shapes)}")
        if any(token in output_names for token in ("boxes", "scores", "labels")):
            signals.append("detection-like output names")
            return TaskGuess("object-detection", 0.7, signals)
        return TaskGuess("image-classification", 0.55, signals)
    if any("seg" in name.lower() for name in [inspection.path, output_names]):
        signals.append("model/output name contains segmentation hint")
        return TaskGuess("segmentation", 0.62, signals)
    if any(token in output_names for token in ("embedding", "embeddings", "sentence")):
        signals.append("embedding-like output name")
        return TaskGuess("embeddings", 0.66, signals)
    if any(token in inspection.path.lower() for token in ("ocr", "text-recognition")):
        signals.append("path contains OCR hint")
        return TaskGuess("OCR", 0.6, signals)
    if any(token in inspection.path.lower() for token in ("whisper", "speech", "audio")):
        signals.append("path contains speech/audio hint")
        return TaskGuess("speech", 0.58, signals)
    return TaskGuess("unknown", 0.15, ["no strong task signal"])


def _onnx_value_info(value: object) -> TensorInfo:
    tensor_type = value.type.tensor_type  # type: ignore[attr-defined]
    shape: list[str] = []
    for dim in tensor_type.shape.dim:
        if dim.dim_param:
            shape.append(dim.dim_param)
        elif dim.dim_value:
            shape.append(str(dim.dim_value))
        else:
            shape.append("?")
    return TensorInfo(name=value.name, shape=shape, dtype=str(tensor_type.elem_type))


def _ov_port_info(port: object) -> TensorInfo:
    shape = [str(dim) for dim in port.partial_shape]  # type: ignore[attr-defined]
    return TensorInfo(
        name=str(getattr(port, "any_name", "")),
        shape=shape,
        dtype=str(getattr(port, "element_type", "")),
    )


def _has_dynamic_shape(tensors: list[TensorInfo]) -> bool:
    return any(
        any(dim in {"?", "-1"} or not dim.isdigit() for dim in item.shape) for item in tensors
    )


def _format_from_path(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "unknown"
