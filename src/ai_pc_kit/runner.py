from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    model: str
    device: str
    iterations: int
    average_ms: float | None
    error: str | None = None


def run_model(model: Path, input_file: Path | None, device: str, iterations: int) -> RunResult:
    try:
        import numpy as np
        import openvino as ov
    except Exception as exc:
        raise RuntimeError(
            "OpenVINO runner dependencies are missing. Install with: "
            "pip install 'accelscope[openvino]'"
        ) from exc

    core = ov.Core()
    compiled = core.compile_model(model, device.upper())
    infer_request = compiled.create_infer_request()
    input_port = compiled.input(0)

    if input_file:
        tensor = np.load(input_file)
    else:
        shape = [dim.get_length() if dim.is_static else 1 for dim in input_port.partial_shape]
        tensor = np.zeros(shape, dtype=_numpy_dtype(input_port.element_type, np))

    infer_request.infer({input_port: tensor})

    started = time.perf_counter()
    for _ in range(iterations):
        infer_request.infer({input_port: tensor})
    elapsed_ms = (time.perf_counter() - started) * 1000

    return RunResult(
        model=str(model),
        device=device.upper(),
        iterations=iterations,
        average_ms=elapsed_ms / iterations,
    )


def compare_devices(
    model: Path,
    input_file: Path | None,
    devices: list[str],
    iterations: int,
) -> list[RunResult]:
    results: list[RunResult] = []
    for device in devices:
        try:
            results.append(
                run_model(
                    model=model,
                    input_file=input_file,
                    device=device,
                    iterations=iterations,
                )
            )
        except Exception as exc:
            results.append(
                RunResult(
                    model=str(model),
                    device=device.upper(),
                    iterations=iterations,
                    average_ms=None,
                    error=str(exc),
                )
            )
    return results


def _numpy_dtype(element_type: object, np: object) -> object:
    text = str(element_type)
    if "f16" in text:
        return np.float16
    if "i64" in text:
        return np.int64
    if "i32" in text:
        return np.int32
    if "u8" in text:
        return np.uint8
    return np.float32
