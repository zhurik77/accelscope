from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ai_pc_kit.capabilities import CapabilityProfile, collect_capabilities
from ai_pc_kit.compatibility import CompatibilityReport, check_compatibility
from ai_pc_kit.model_inspector import ModelInspection, inspect_model
from ai_pc_kit.runner import RunResult, compare_devices
from ai_pc_kit.runtimes import RuntimeProfile, scan_runtimes


@dataclass
class RouteChoice:
    backend: str
    device: str
    reason: str


@dataclass
class RouteRecommendation:
    model: ModelInspection
    hardware: CapabilityProfile
    runtimes: RuntimeProfile
    compatibility: CompatibilityReport
    best_default: RouteChoice | None
    best_latency: RouteChoice | None
    best_compatibility: RouteChoice | None
    best_battery_candidate: RouteChoice | None
    fallback: RouteChoice | None
    avoid: list[RouteChoice] = field(default_factory=list)
    benchmarks: list[RunResult] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def recommend_route(
    path: Path,
    *,
    run_benchmark: bool = False,
    iterations: int = 5,
) -> RouteRecommendation:
    hardware = collect_capabilities()
    runtimes = scan_runtimes()
    model = inspect_model(path)
    compatibility = check_compatibility(path)
    working = [item for item in compatibility.results if item.estimated_support == "works"]
    benchmarks: list[RunResult] = []
    warnings: list[str] = []

    if run_benchmark and working:
        devices = [item.device for item in working]
        benchmarks = compare_devices(path, input_file=None, devices=devices, iterations=iterations)

    best_latency = _best_latency(benchmarks)
    best_compatibility = _first_working(working)
    fallback = _fallback(working)
    battery = _battery_candidate(working)
    best_default = best_latency or _preferred_default(working)
    avoid = _avoid_list(compatibility, benchmarks, best_default)
    confidence = _confidence(model, compatibility, benchmarks, iterations)

    if model.error:
        warnings.append(model.error)
    if not working:
        warnings.append("No OpenVINO device successfully compiled this model.")

    return RouteRecommendation(
        model=model,
        hardware=hardware,
        runtimes=runtimes,
        compatibility=compatibility,
        best_default=best_default,
        best_latency=best_latency,
        best_compatibility=best_compatibility,
        best_battery_candidate=battery,
        fallback=fallback,
        avoid=avoid,
        benchmarks=benchmarks,
        confidence=confidence,
        warnings=warnings,
    )


def _best_latency(results: list[RunResult]) -> RouteChoice | None:
    successful = [item for item in results if item.average_ms is not None]
    if not successful:
        return None
    fastest = min(successful, key=lambda item: item.average_ms or float("inf"))
    return RouteChoice(
        backend="openvino",
        device=fastest.device,
        reason=f"Lowest observed latency: {fastest.average_ms:.2f} ms.",
    )


def _first_working(working: list[object]) -> RouteChoice | None:
    if not working:
        return None
    result = working[0]
    return RouteChoice(
        backend="openvino",
        device=result.device,
        reason="First runtime/device path that compiled successfully.",
    )


def _preferred_default(working: list[object]) -> RouteChoice | None:
    order = ["GPU", "NPU", "CPU", "AUTO"]
    by_device = {item.device: item for item in working}
    for device in order:
        if device in by_device:
            return RouteChoice(
                backend="openvino",
                device=device,
                reason="Preferred working device based on local AI PC routing heuristics.",
            )
    return None


def _fallback(working: list[object]) -> RouteChoice | None:
    for item in working:
        if item.device == "CPU":
            return RouteChoice(
                "openvino",
                "CPU",
                "CPU compiled successfully and is the safest fallback.",
            )
    if working:
        item = working[0]
        return RouteChoice("openvino", item.device, "Only available compiled fallback.")
    return None


def _battery_candidate(working: list[object]) -> RouteChoice | None:
    for device in ("NPU", "GPU", "CPU"):
        if any(item.device == device for item in working):
            return RouteChoice(
                "openvino",
                device,
                "Candidate for battery-friendly routing; measure power externally for certainty.",
            )
    return None


def _avoid_list(
    compatibility: CompatibilityReport,
    benchmarks: list[RunResult],
    best_default: RouteChoice | None,
) -> list[RouteChoice]:
    avoid: list[RouteChoice] = []
    for item in compatibility.results:
        if item.estimated_support == "fails":
            avoid.append(
                RouteChoice(
                    item.backend,
                    item.device,
                    item.friendly_reason or "This path failed compatibility.",
                )
            )
    successful = [item for item in benchmarks if item.average_ms is not None]
    auto = next((item for item in successful if item.device == "AUTO"), None)
    if auto and best_default and best_default.device != "AUTO":
        explicit = next((item for item in successful if item.device == best_default.device), None)
        if (
            explicit
            and auto.average_ms
            and explicit.average_ms
            and auto.average_ms > explicit.average_ms
        ):
            avoid.append(
                RouteChoice(
                    "openvino",
                    "AUTO",
                    "AUTO was slower than the recommended explicit device.",
                )
            )
    return avoid


def _confidence(
    model: ModelInspection,
    compatibility: CompatibilityReport,
    benchmarks: list[RunResult],
    iterations: int,
) -> float:
    score = 0.2
    if model.exists and not model.error:
        score += 0.2 * model.task.confidence
    if any(item.estimated_support == "works" for item in compatibility.results):
        score += 0.25
    if benchmarks and any(item.average_ms is not None for item in benchmarks):
        score += 0.25
        score += min(iterations, 25) / 25 * 0.1
    return round(min(score, 0.95), 2)
