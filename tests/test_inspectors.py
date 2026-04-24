from ai_pc_kit.inspectors import AiPcReport, OpenVinoInfo, render_report
from rich.console import Console


def test_render_json_report() -> None:
    console = Console(record=True)
    report = AiPcReport(
        os="Windows 11",
        python="3.12.0",
        ram_gb=24.0,
        openvino=OpenVinoInfo(installed=False),
    )

    render_report(report, console=console, json_output=True)

    output = console.export_text()
    assert '"ram_gb": 24.0' in output
    assert '"installed": false' in output


def test_report_recommendations_render() -> None:
    console = Console(record=True)
    report = AiPcReport(
        os="Windows 11",
        python="3.14.0",
        ram_gb=24.0,
        openvino=OpenVinoInfo(installed=False),
        recommendations=["Install Python 3.12."],
    )

    render_report(report, console=console)

    assert "Recommendations" in console.export_text()
