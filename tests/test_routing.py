import json
from pathlib import Path

from ai_pc_kit.compatibility import check_compatibility
from ai_pc_kit.recommendations import recommend_route
from ai_pc_kit.routing import routing_manifest


def test_compatibility_collects_per_device_failures(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    report = check_compatibility(missing, devices=["CPU", "GPU"])

    assert len(report.results) == 2
    assert {item.device for item in report.results} == {"CPU", "GPU"}


def test_route_manifest_is_json_serializable_for_missing_model(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    recommendation = recommend_route(missing, run_benchmark=False)
    manifest = routing_manifest(recommendation)

    assert manifest["model"]["path"].endswith("missing.xml")
    assert "recommendation" in manifest
    json.dumps(manifest)
