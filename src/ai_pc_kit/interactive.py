from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ai_pc_kit.backends import list_backends
from ai_pc_kit.catalog import list_models
from ai_pc_kit.inspectors import collect_report, render_report
from ai_pc_kit.model_zoo import download_model
from ai_pc_kit.reports import write_benchmark_report
from ai_pc_kit.runner import compare_devices


@dataclass(frozen=True)
class Intent:
    name: str
    description: str


MENU_TEXT = """Choose an action:

  1. Inspect hardware
  2. Show OpenVINO devices
  3. Run benchmark
  4. Show model templates
  5. Show backends
  6. Help
  0. Exit
"""

HELP_TEXT = """You can choose menu numbers or type short commands:

  1 / inspect / железо
  2 / devices / устройства
  3 / benchmark / бенчмарк
  4 / models / модели
  5 / backends / бэкенды
  0 / exit / выход

Examples:
  1
  3
  benchmark
"""


def run_interactive(console: Console | None = None) -> None:
    console = console or Console()
    console.print("[bold]AccelScope[/bold]")
    console.print("Menu mode. Pick a number and press Enter.\n")

    while True:
        console.print(MENU_TEXT)
        try:
            text = console.input("[bold cyan]Select>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nbye")
            return

        if not text:
            continue

        intent = detect_intent(text)
        if intent.name == "exit":
            console.print("bye")
            return

        handle_intent(intent, console)


def detect_intent(text: str) -> Intent:
    normalized = text.strip().lower()

    if normalized in {"0", "exit", "quit", "q", "выход", "выйти", "закрыть"}:
        return Intent("exit", "Exit interactive mode.")

    if normalized in {"6", "?"} or _has_any(normalized, "help", "помощ", "что ты умеешь"):
        return Intent("help", "Show help.")

    if normalized == "2" or _has_any(normalized, "device", "devices", "устрой", "openvino", "девайс"):
        return Intent("devices", "Show OpenVINO runtime devices.")

    if normalized == "3" or _has_any(normalized, "benchmark", "bench", "бенч", "тест", "протест", "сравн"):
        return Intent("benchmark", "Run the default benchmark.")

    if normalized == "4" or _has_any(normalized, "model", "models", "модел"):
        return Intent("models", "List model templates.")

    if normalized == "5" or _has_any(normalized, "backend", "backends", "бэкенд", "бекенд", "cuda", "rocm", "directml"):
        return Intent("backends", "List backends.")

    if normalized == "1" or _has_any(normalized, "inspect", "hardware", "желез", "ноут", "комп", "проверь", "диагност"):
        return Intent("inspect", "Inspect local hardware.")

    return Intent("unknown", "Unknown request.")


def handle_intent(intent: Intent, console: Console) -> None:
    if intent.name == "help":
        console.print(HELP_TEXT)
        return

    if intent.name == "inspect":
        render_report(collect_report(), console=console)
        return

    if intent.name == "devices":
        _show_devices(console)
        return

    if intent.name == "benchmark":
        _run_default_benchmark(console)
        return

    if intent.name == "models":
        _show_models(console)
        return

    if intent.name == "backends":
        _show_backends(console)
        return

    console.print("Unknown choice. Pick a number from the menu.")


def _show_devices(console: Console) -> None:
    report = collect_report(include_system=False)
    openvino = report.openvino
    if not openvino.installed:
        console.print("[yellow]OpenVINO is not installed.[/yellow]")
        console.print("Install with: pip install 'accelscope[openvino]'")
        return

    console.print(f"OpenVINO: [bold]{openvino.version or 'unknown'}[/bold]")
    for device in openvino.devices:
        console.print(f"- {device}")


def _run_default_benchmark(console: Console) -> None:
    key = "object-detection"
    output = Path("benchmark.md")
    console.print("Running default benchmark: object-detection on CPU,GPU,NPU,AUTO")

    try:
        download = download_model(key=key, output_dir=Path("models"), convert=True)
    except Exception as exc:
        console.print(f"[red]Benchmark setup failed:[/red] {exc}")
        return

    if download.model_xml is None:
        console.print("[red]Benchmark setup failed:[/red] no OpenVINO .xml model was found.")
        return

    results = compare_devices(
        model=download.model_xml,
        input_file=None,
        devices=["CPU", "GPU", "NPU", "AUTO"],
        iterations=10,
    )
    write_benchmark_report(output, results)
    console.print(f"Wrote benchmark report: [bold]{output}[/bold]")
    _render_results(console, f"Benchmark: {key}", results)


def _show_models(console: Console) -> None:
    table = Table(title="Model Task Templates")
    table.add_column("Key")
    table.add_column("Backend")
    table.add_column("Devices")

    for entry in list_models():
        table.add_row(entry.key, entry.backend, ", ".join(entry.recommended_devices))

    console.print(table)


def _show_backends(console: Console) -> None:
    table = Table(title="Inference Backends")
    table.add_column("Key")
    table.add_column("Devices")
    table.add_column("Notes")

    for backend in list_backends():
        table.add_row(backend.key, ", ".join(backend.devices), backend.notes)

    console.print(table)


def _render_results(console: Console, title: str, results: object) -> None:
    table = Table(title=title)
    table.add_column("Device")
    table.add_column("Status")
    table.add_column("Average latency")
    table.add_column("Details")

    for result in results:
        table.add_row(
            result.device,
            "ok" if result.error is None else "failed",
            "" if result.average_ms is None else f"{result.average_ms:.2f} ms",
            result.error or "",
        )

    console.print(table)


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)
