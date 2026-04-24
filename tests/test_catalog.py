from ai_pc_kit.catalog import get_model, list_models


def test_catalog_has_gpu_and_npu_templates() -> None:
    entries = list_models()

    assert entries
    assert get_model("object-detection") is not None
    assert any("GPU" in entry.recommended_devices for entry in entries)
    assert any("NPU" in entry.recommended_devices for entry in entries)
    assert get_model("image-classification").download is not None
