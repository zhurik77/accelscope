from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

import typer
from rich.console import Console

from ai_pc_kit.backends import get_backend, list_backends
from ai_pc_kit.catalog import get_model, list_models
from ai_pc_kit.inspectors import collect_report, render_report
from ai_pc_kit.interactive import run_interactive
from ai_pc_kit.model_zoo import download_model
from ai_pc_kit.reports import benchmark_json, write_benchmark_report
from ai_pc_kit.runner import compare_devices, run_model

app = typer.Typer(
    name="accelscope",
    help="Inspect and benchmark local AI accelerators across CPU, GPU, and NPU.",
    no_args_is_help=True,
)
models_app = typer.Typer(help="Browse model task templates for CPU, GPU, NPU, and AUTO runs.")
backends_app = typer.Typer(help="Browse supported and planned inference backends.")
app.add_typer(models_app, name="models")
app.add_typer(backends_app, name="backends")
console = Console()


@app.command()
def inspect(
    json_output: bool = typer.Option(False, "--json", help="Print a machine-readable JSON report."),
) -> None:
    """Inspect local AI PC capabilities."""
    report = collect_report()
    render_report(report, console=console, json_output=json_output)


@app.command()
def devices() -> None:
    """List OpenVINO runtime devices if OpenVINO is installed."""
    report = collect_report(include_system=False)
    openvino = report.openvino

    if not openvino.installed:
        console.print("[yellow]OpenVINO is not installed.[/yellow]")
        console.print("Install with: [bold]pip install 'accelscope\\[openvino]'[/bold]")
        raise typer.Exit(code=1)

    console.print(f"OpenVINO: [bold]{openvino.version or 'unknown'}[/bold]")
    for device in openvino.devices:
        console.print(f"- {device}")


@app.command("run")
def run(
    model: Path = typer.Argument(..., exists=True, readable=True, help="Path to an OpenVINO .xml model."),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="Optional .npy input tensor. If omitted, a zero tensor is generated.",
    ),
    device: str = typer.Option("AUTO", "--device", "-d", help="OpenVINO device: CPU, GPU, NPU, or AUTO."),
    iterations: int = typer.Option(10, "--iterations", "-n", min=1, help="Number of inference runs."),
) -> None:
    """Run a simple benchmark against an OpenVINO IR model."""
    result = run_model(model=model, input_file=input_file, device=device, iterations=iterations)
    console.print(f"Device: [bold]{result.device}[/bold]")
    console.print(f"Model: {result.model}")
    console.print(f"Iterations: {result.iterations}")
    console.print(f"Average latency: [bold]{result.average_ms:.2f} ms[/bold]")


@app.command("compare")
def compare(
    model: Path = typer.Argument(..., exists=True, readable=True, help="Path to an OpenVINO .xml model."),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="Optional .npy input tensor. If omitted, a zero tensor is generated.",
    ),
    devices: str = typer.Option(
        "CPU,GPU,NPU,AUTO",
        "--devices",
        help="Comma-separated OpenVINO devices to test.",
    ),
    iterations: int = typer.Option(10, "--iterations", "-n", min=1, help="Number of inference runs."),
    json_output: bool = typer.Option(False, "--json", help="Print a machine-readable JSON report."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write benchmark report to .json or .md.",
    ),
) -> None:
    """Compare model latency across CPU, GPU, NPU, and AUTO."""
    from rich.table import Table

    requested_devices = [item.strip().upper() for item in devices.split(",") if item.strip()]
    results = compare_devices(
        model=model,
        input_file=input_file,
        devices=requested_devices,
        iterations=iterations,
    )

    if output:
        write_benchmark_report(output, results)
        console.print(f"Wrote benchmark report: [bold]{output}[/bold]")

    if json_output:
        console.print(benchmark_json(results))
        return

    table = Table(title="Device Comparison")
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


@app.command("benchmark")
def benchmark(
    key: str = typer.Argument("object-detection", help="Model task key from `accelscope models list`."),
    output_dir: Path = typer.Option(Path("models"), "--model-dir", help="Directory for downloaded models."),
    devices: str = typer.Option(
        "CPU,GPU,NPU,AUTO",
        "--devices",
        help="Comma-separated OpenVINO devices to test.",
    ),
    iterations: int = typer.Option(10, "--iterations", "-n", min=1, help="Number of inference runs."),
    output: Optional[Path] = typer.Option(
        Path("benchmark.md"),
        "--output",
        "-o",
        help="Write benchmark report to .json or .md.",
    ),
) -> None:
    """Download a known-good model and benchmark it across local devices."""
    from rich.table import Table

    try:
        download = download_model(key=key, output_dir=output_dir, convert=True)
    except Exception as exc:
        console.print(f"[red]Benchmark setup failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if download.model_xml is None:
        console.print("[red]Benchmark setup failed:[/red] no OpenVINO .xml model was found.")
        raise typer.Exit(code=1)

    requested_devices = [item.strip().upper() for item in devices.split(",") if item.strip()]
    results = compare_devices(
        model=download.model_xml,
        input_file=None,
        devices=requested_devices,
        iterations=iterations,
    )

    if output:
        write_benchmark_report(output, results)
        console.print(f"Wrote benchmark report: [bold]{output}[/bold]")

    table = Table(title=f"Benchmark: {key}")
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


@models_app.command("list")
def models_list() -> None:
    """List built-in model task templates."""
    from rich.table import Table

    table = Table(title="Model Task Templates")
    table.add_column("Key")
    table.add_column("Task")
    table.add_column("Backend")
    table.add_column("Devices")

    for entry in list_models():
        table.add_row(entry.key, entry.task, entry.backend, ", ".join(entry.recommended_devices))

    console.print(table)


@models_app.command("info")
def models_info(key: str = typer.Argument(..., help="Model task key from `accelscope models list`.")) -> None:
    """Show details for a model task template."""
    entry = get_model(key)
    if entry is None:
        console.print(f"[red]Unknown model task:[/red] {key}")
        raise typer.Exit(code=1)

    console.print(f"[bold]{entry.key}[/bold]")
    console.print(entry.task)
    console.print(f"Backend: {entry.backend}")
    console.print(f"Download: {entry.download or 'manual'}")
    console.print(f"Recommended devices: {', '.join(entry.recommended_devices)}")
    console.print(f"Notes: {entry.notes}")
    console.print(f"Example: [bold]{entry.example_command}[/bold]")


@models_app.command("download")
def models_download(
    key: str = typer.Argument(..., help="Model task key from `accelscope models list`."),
    output_dir: Path = typer.Option(Path("models"), "--output-dir", "-o", help="Model output directory."),
    convert: bool = typer.Option(True, "--convert/--no-convert", help="Convert to OpenVINO IR when needed."),
) -> None:
    """Download a known-good model for a task template."""
    try:
        result = download_model(key=key, output_dir=output_dir, convert=convert)
    except Exception as exc:
        console.print(f"[red]Model download failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"Downloaded model template: [bold]{result.model_key}[/bold]")
    console.print(f"Output directory: {result.output_dir}")
    if result.model_xml:
        console.print(f"OpenVINO IR: [bold]{result.model_xml}[/bold]")
        console.print(
            "Try: "
            f"[bold]accelscope compare {result.model_xml} --devices CPU,GPU,NPU,AUTO --iterations 50[/bold]"
        )
    for command in result.commands:
        console.print(f"[dim]ran: {command}[/dim]")


@backends_app.command("list")
def backends_list() -> None:
    """List supported and planned inference backends."""
    from rich.table import Table

    table = Table(title="Inference Backends")
    table.add_column("Key")
    table.add_column("Scope")
    table.add_column("Devices")

    for backend in list_backends():
        table.add_row(backend.key, backend.scope, ", ".join(backend.devices))

    console.print(table)


@backends_app.command("info")
def backends_info(key: str = typer.Argument(..., help="Backend key from `accelscope backends list`.")) -> None:
    """Show backend details."""
    backend = get_backend(key)
    if backend is None:
        console.print(f"[red]Unknown backend:[/red] {key}")
        raise typer.Exit(code=1)

    console.print(f"[bold]{backend.key}[/bold]")
    console.print(backend.scope)
    console.print(f"Devices/providers: {', '.join(backend.devices)}")
    console.print(f"Notes: {backend.notes}")


def main() -> None:
    if len(sys.argv) == 1:
        run_interactive(console)
        return

    app()


if __name__ == "__main__":
    main()
