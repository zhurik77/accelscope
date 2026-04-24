from __future__ import annotations

import json
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ai_pc_kit.runner import RunResult


def benchmark_payload(results: list[RunResult]) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "results": [asdict(result) for result in results],
    }


def benchmark_json(results: list[RunResult]) -> str:
    return json.dumps(benchmark_payload(results), ensure_ascii=False, indent=2)


def benchmark_markdown(results: list[RunResult]) -> str:
    lines = [
        "# AI PC Benchmark",
        "",
        f"- Created: {datetime.now(timezone.utc).isoformat()}",
        f"- Host: {platform.node()}",
        "",
        "| Device | Status | Average latency | Details |",
        "| --- | --- | ---: | --- |",
    ]

    for result in results:
        status = "ok" if result.error is None else "failed"
        latency = "" if result.average_ms is None else f"{result.average_ms:.2f} ms"
        details = _escape_markdown_cell(result.error or "")
        lines.append(f"| {result.device} | {status} | {latency} | {details} |")

    lines.append("")
    return "\n".join(lines)


def write_benchmark_report(path: Path, results: list[RunResult], fmt: str | None = None) -> None:
    report_format = (fmt or _format_from_path(path)).lower()
    if report_format == "json":
        path.write_text(benchmark_json(results), encoding="utf-8")
        return
    if report_format in {"md", "markdown"}:
        path.write_text(benchmark_markdown(results), encoding="utf-8")
        return
    raise ValueError(f"Unsupported report format: {report_format}")


def _format_from_path(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "json"


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
