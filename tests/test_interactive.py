from ai_pc_kit.interactive import detect_intent


def test_detect_russian_benchmark_intent() -> None:
    assert detect_intent("сделай бенчмарк").name == "benchmark"


def test_detect_russian_inspect_intent() -> None:
    assert detect_intent("проверь железо").name == "inspect"


def test_detect_exit_intent() -> None:
    assert detect_intent("выход").name == "exit"


def test_detect_numbered_menu_intent() -> None:
    assert detect_intent("1").name == "inspect"
    assert detect_intent("2").name == "devices"
    assert detect_intent("3").name == "benchmark"
    assert detect_intent("0").name == "exit"
