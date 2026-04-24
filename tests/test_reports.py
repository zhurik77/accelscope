import json

from ai_pc_kit.reports import benchmark_json, benchmark_markdown
from ai_pc_kit.runner import RunResult


def test_benchmark_json_contains_results() -> None:
    data = benchmark_json(
        [RunResult(model="model.xml", device="GPU", iterations=5, average_ms=1.25)]
    )

    payload = json.loads(data)
    assert payload["schema_version"] == "0.1"
    assert payload["results"][0]["device"] == "GPU"


def test_benchmark_markdown_contains_failed_device() -> None:
    markdown = benchmark_markdown(
        [RunResult(model="model.xml", device="NPU", iterations=5, average_ms=None, error="nope")]
    )

    assert "| NPU | failed |  | nope |" in markdown
