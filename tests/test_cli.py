from typer.testing import CliRunner

from ai_pc_kit.cli import app


def test_help_keeps_existing_commands_and_adds_tui() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "devices" in result.output
    assert "benchmark" in result.output
    assert "compare" in result.output
    assert "models" in result.output
    assert "backends" in result.output
    assert "tui" in result.output
    assert "doctor" in result.output
    assert "menu" in result.output
