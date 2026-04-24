from ai_pc_kit.runtimes import scan_runtimes


def test_runtime_scan_does_not_require_optional_backends() -> None:
    profile = scan_runtimes().to_dict()
    keys = {item["key"] for item in profile["runtimes"]}

    assert "openvino" in keys
    assert "onnxruntime" in keys
    assert "directml" in keys
