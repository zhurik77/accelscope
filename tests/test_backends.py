from ai_pc_kit.backends import get_backend, list_backends


def test_backends_include_non_intel_paths() -> None:
    keys = {backend.key for backend in list_backends()}

    assert "openvino" in keys
    assert "cuda" in keys
    assert "rocm" in keys
    assert get_backend("directml") is not None
