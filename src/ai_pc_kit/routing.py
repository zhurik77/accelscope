from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_pc_kit.recommendations import RouteRecommendation


def routing_manifest(recommendation: RouteRecommendation) -> dict[str, Any]:
    hardware = recommendation.hardware
    model = recommendation.model
    return {
        "model": {
            "path": model.path,
            "format": model.format,
            "task_guess": model.task.task_guess,
            "confidence": model.task.confidence,
            "opset": model.opset,
        },
        "machine": {
            "cpu": hardware.cpu.name if hardware.cpu else None,
            "gpus": [asdict(item) for item in hardware.gpus],
            "npus": [asdict(item) for item in hardware.npus],
            "ram_gb": hardware.memory.total_gb,
            "os": hardware.system.os_name,
        },
        "recommendation": {
            "best_default": _choice(recommendation.best_default),
            "best_latency": _choice(recommendation.best_latency),
            "best_compatibility": _choice(recommendation.best_compatibility),
            "best_battery_candidate": _choice(recommendation.best_battery_candidate),
            "fallback": _choice(recommendation.fallback),
            "avoid": [_choice(item) for item in recommendation.avoid],
            "confidence": recommendation.confidence,
        },
        "benchmarks": [asdict(item) for item in recommendation.benchmarks],
        "compatibility": [asdict(item) for item in recommendation.compatibility.results],
        "warnings": recommendation.warnings,
    }


def write_routing_manifest(path: Path, recommendation: RouteRecommendation) -> None:
    path.write_text(json.dumps(routing_manifest(recommendation), indent=2), encoding="utf-8")


def _choice(choice: object | None) -> dict[str, str] | None:
    if choice is None:
        return None
    return asdict(choice)
