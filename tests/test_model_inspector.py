from pathlib import Path

from ai_pc_kit.model_inspector import inspect_model


def test_model_inspector_handles_missing_file(tmp_path: Path) -> None:
    result = inspect_model(tmp_path / "missing.onnx")

    assert result.exists is False
    assert result.error == "Model file does not exist."


def test_model_inspector_handles_unsupported_extension(tmp_path: Path) -> None:
    model = tmp_path / "model.txt"
    model.write_text("not a model", encoding="utf-8")

    result = inspect_model(model)

    assert result.exists is True
    assert result.format == "txt"
    assert "Unsupported model extension" in (result.error or "")
