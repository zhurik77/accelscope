from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

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
def tui() -> None:
    """Open the keyboard and mouse driven terminal UI."""
    from ai_pc_kit.tui import run_tui

    run_tui()


@app.command()
def menu(
    classic: bool = typer.Option(
        False,
        "--classic",
        help="Open the legacy number-based menu instead of the Textual TUI.",
    ),
) -> None:
    """Open an interactive menu."""
    if classic:
        run_interactive(console)
        return

    from ai_pc_kit.tui import run_tui

    run_tui()


@app.command()
def doctor() -> None:
    """Run a basic local AI runtime diagnostic."""
    report = collect_report()
    openvino = report.openvino

    table = Table(title="AccelScope Doctor")
    table.add_column("Check")
    table.add_column("Result")
    table.add_column("Recommendation")

    table.add_row("OS", report.os, "ok")
    table.add_row("Python", report.python, "Use Python 3.10-3.12 for the OpenVINO path.")
    table.add_row(
        "OpenVINO",
        openvino.version or ("installed" if openvino.installed else "missing"),
        "Install with: pip install 'accelscope[openvino]'" if not openvino.installed else "ok",
    )
    table.add_row(
        "OpenVINO devices",
        ", ".join(openvino.devices) or "none",
        "Run accelscope devices for the raw runtime view.",
    )
    table.add_row(
        "CPU",
        report.cpu.name if report.cpu and report.cpu.name else "unknown",
        "CPU is the baseline path.",
    )
    table.add_row(
        "GPU",
        ", ".join(gpu.name for gpu in report.gpus) or "none detected",
        "Include GPU in every comparison if present.",
    )
    table.add_row(
        "NPU",
        ", ".join(npu.name for npu in report.npus) or "none detected",
        "If NPU is present in Device Manager but missing here, check driver/runtime support.",
    )
    table.add_row(
        "Model cache",
        "present" if Path("models").exists() else "empty",
        "Next: accelscope benchmark object-detection --iterations 10",
    )

    console.print(table)
    if not openvino.installed:
        console.print("[yellow]Warning:[/yellow] OpenVINO is missing or failed to load.")
        if openvino.error:
            console.print(f"[dim]{openvino.error}[/dim]")
    elif "NPU" not in openvino.devices:
        console.print("[yellow]Warning:[/yellow] no OpenVINO NPU device is visible.")


@app.command("profile")
def profile(
    json_output: bool = typer.Option(False, "--json", help="Print normalized JSON."),
) -> None:
    """Scan the normalized AI PC hardware capability profile."""
    from ai_pc_kit.capabilities import collect_capabilities

    capability = collect_capabilities()
    if json_output:
        console.print(json.dumps(capability.to_dict(), ensure_ascii=False, indent=2))
        return

    table = Table(title="AI PC Capability Profile")
    table.add_column("Area")
    table.add_column("Value")
    table.add_column("Notes")
    table.add_row("OS", capability.system.windows_version or capability.system.os_name, capability.system.os_build or "")
    table.add_row("Architecture", capability.system.architecture, "")
    table.add_row("Python", capability.system.python_version, f"AccelScope {capability.system.accelscope_version}")
    table.add_row("Power", capability.system.power_mode or "unknown", capability.system.battery_status or "")
    table.add_row(
        "CPU",
        capability.cpu.name if capability.cpu and capability.cpu.name else "unknown",
        capability.cpu.vendor if capability.cpu else "",
    )
    for gpu in capability.gpus:
        table.add_row("GPU", gpu.name, gpu.vendor or "unknown")
    for npu in capability.npus:
        table.add_row("NPU", npu.name, npu.vendor or "unknown")
    table.add_row(
        "Memory",
        f"{capability.memory.total_gb} GB total / {capability.memory.available_gb} GB available",
        capability.memory.type or "type unknown",
    )
    console.print(table)
    for warning in capability.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


@app.command("runtimes")
def runtimes(
    json_output: bool = typer.Option(False, "--json", help="Print normalized JSON."),
) -> None:
    """Scan installed and planned local AI runtimes/providers."""
    from ai_pc_kit.runtimes import scan_runtimes

    profile = scan_runtimes()
    if json_output:
        console.print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return

    table = Table(title="Runtime Capability Profile")
    table.add_column("Runtime")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("Devices/providers")
    table.add_column("Hint")
    for runtime in profile.runtimes:
        status = "installed" if runtime.installed else runtime.status
        targets = ", ".join(runtime.devices or runtime.providers) or ""
        table.add_row(runtime.key, status, runtime.version or "", targets, runtime.install_hint or "")
    console.print(table)


@app.command("inspect-model")
def inspect_model_command(
    path: Path = typer.Argument(..., help="Path to .onnx or OpenVINO .xml model."),
    json_output: bool = typer.Option(False, "--json", help="Print normalized JSON."),
) -> None:
    """Inspect ONNX or OpenVINO IR model metadata."""
    from ai_pc_kit.model_inspector import inspect_model

    inspection = inspect_model(path)
    if json_output:
        console.print(json.dumps(inspection.to_dict(), ensure_ascii=False, indent=2))
        return
    _render_model_inspection(inspection)


@app.command("compatibility")
def compatibility_command(
    path: Path = typer.Argument(..., help="Path to .onnx or OpenVINO .xml model."),
    json_output: bool = typer.Option(False, "--json", help="Print normalized JSON."),
) -> None:
    """Check which OpenVINO device paths can compile a model."""
    from ai_pc_kit.compatibility import check_compatibility

    report = check_compatibility(path)
    if json_output:
        console.print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return
    table = Table(title=f"Compatibility: {path.name}")
    table.add_column("Backend")
    table.add_column("Device")
    table.add_column("Available")
    table.add_column("Support")
    table.add_column("Reason")
    for result in report.results:
        table.add_row(
            result.backend,
            result.device,
            "yes" if result.available else "no",
            result.estimated_support,
            result.friendly_reason or result.error_message or "",
        )
    console.print(table)


@app.command("recommend")
def recommend_command(
    path: Path = typer.Argument(..., help="Path to .onnx or OpenVINO .xml model."),
    benchmark: bool = typer.Option(False, "--benchmark", help="Run a short benchmark on working paths."),
    iterations: int = typer.Option(5, "--iterations", "-n", min=1, help="Benchmark iterations."),
    json_output: bool = typer.Option(False, "--json", help="Print normalized JSON."),
) -> None:
    """Recommend the best backend/device route for a model on this machine."""
    from ai_pc_kit.recommendations import recommend_route

    recommendation = recommend_route(path, run_benchmark=benchmark, iterations=iterations)
    if json_output:
        console.print(json.dumps(recommendation.to_dict(), ensure_ascii=False, indent=2))
        return
    _render_recommendation(recommendation)


@app.command("route")
def route_command(
    path: Path = typer.Argument(..., help="Path to .onnx or OpenVINO .xml model."),
    output: Path = typer.Option(
        Path("accelscope.routing.json"),
        "--output",
        "-o",
        help="Write routing manifest JSON.",
    ),
    benchmark: bool = typer.Option(False, "--benchmark", help="Run a short benchmark first."),
    iterations: int = typer.Option(5, "--iterations", "-n", min=1, help="Benchmark iterations."),
) -> None:
    """Export a routing manifest for app developers."""
    from ai_pc_kit.recommendations import recommend_route
    from ai_pc_kit.routing import write_routing_manifest

    recommendation = recommend_route(path, run_benchmark=benchmark, iterations=iterations)
    write_routing_manifest(output, recommendation)
    console.print(f"Wrote routing manifest: [bold]{output}[/bold]")


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
    model: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to an OpenVINO .xml model."
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="Optional .npy input tensor. If omitted, a zero tensor is generated.",
    ),
    device: str = typer.Option(
        "AUTO", "--device", "-d", help="OpenVINO device: CPU, GPU, NPU, or AUTO."
    ),
    iterations: int = typer.Option(
        10, "--iterations", "-n", min=1, help="Number of inference runs."
    ),
) -> None:
    """Run a simple benchmark against an OpenVINO IR model."""
    result = run_model(model=model, input_file=input_file, device=device, iterations=iterations)
    console.print(f"Device: [bold]{result.device}[/bold]")
    console.print(f"Model: {result.model}")
    console.print(f"Iterations: {result.iterations}")
    console.print(f"Average latency: [bold]{result.average_ms:.2f} ms[/bold]")


@app.command("compare")
def compare(
    model: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to an OpenVINO .xml model."
    ),
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
    iterations: int = typer.Option(
        10, "--iterations", "-n", min=1, help="Number of inference runs."
    ),
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
    key: str = typer.Argument(
        "object-detection", help="Model task key from `accelscope models list`."
    ),
    output_dir: Path = typer.Option(
        Path("models"), "--model-dir", help="Directory for downloaded models."
    ),
    devices: str = typer.Option(
        "CPU,GPU,NPU,AUTO",
        "--devices",
        help="Comma-separated OpenVINO devices to test.",
    ),
    iterations: int = typer.Option(
        10, "--iterations", "-n", min=1, help="Number of inference runs."
    ),
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
def models_info(
    key: str = typer.Argument(..., help="Model task key from `accelscope models list`."),
) -> None:
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
    output_dir: Path = typer.Option(
        Path("models"), "--output-dir", "-o", help="Model output directory."
    ),
    convert: bool = typer.Option(
        True, "--convert/--no-convert", help="Convert to OpenVINO IR when needed."
    ),
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
def backends_info(
    key: str = typer.Argument(..., help="Backend key from `accelscope backends list`."),
) -> None:
    """Show backend details."""
    backend = get_backend(key)
    if backend is None:
        console.print(f"[red]Unknown backend:[/red] {key}")
        raise typer.Exit(code=1)

    console.print(f"[bold]{backend.key}[/bold]")
    console.print(backend.scope)
    console.print(f"Devices/providers: {', '.join(backend.devices)}")
    console.print(f"Notes: {backend.notes}")


def _render_model_inspection(inspection: object) -> None:
    console.print(f"[bold]Model:[/bold] {inspection.path}")
    console.print(f"Format: {inspection.format}")
    console.print(f"Size: {inspection.size_bytes or 0} bytes")
    if inspection.error:
        console.print(f"[yellow]{inspection.error}[/yellow]")
    if inspection.opset:
        console.print(f"Opset: {inspection.opset}")
    console.print(
        f"Task guess: [bold]{inspection.task.task_guess}[/bold] "
        f"(confidence {inspection.task.confidence:.2f})"
    )
    for signal in inspection.task.signals:
        console.print(f"- {signal}")

    table = Table(title="Model IO")
    table.add_column("Kind")
    table.add_column("Name")
    table.add_column("Shape")
    table.add_column("Type")
    for item in inspection.inputs:
        table.add_row("input", item.name, "x".join(item.shape), item.dtype or "")
    for item in inspection.outputs:
        table.add_row("output", item.name, "x".join(item.shape), item.dtype or "")
    console.print(table)

    if inspection.operator_types:
        ops = ", ".join(f"{key}:{value}" for key, value in inspection.operator_types.items())
        console.print(f"Operators: {ops}")


def _render_recommendation(recommendation: object) -> None:
    console.print("[bold]Recommended route[/bold]")
    if recommendation.best_default is None:
        console.print("[yellow]No working route found.[/yellow]")
    else:
        console.print(f"Backend: [bold]{recommendation.best_default.backend}[/bold]")
        console.print(f"Device: [bold]{recommendation.best_default.device}[/bold]")
        console.print(f"Reason: {recommendation.best_default.reason}")

    if recommendation.fallback:
        console.print(
            f"Fallback: {recommendation.fallback.backend} {recommendation.fallback.device} "
            f"- {recommendation.fallback.reason}"
        )

    if recommendation.avoid:
        console.print("[bold]Avoid[/bold]")
        for item in recommendation.avoid:
            console.print(f"- {item.backend} {item.device}: {item.reason}")

    console.print(f"Recommendation confidence: [bold]{recommendation.confidence:.2f}[/bold]")
    for warning in recommendation.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    if recommendation.benchmarks:
        table = Table(title="Benchmark observations")
        table.add_column("Device")
        table.add_column("Status")
        table.add_column("Average latency")
        for result in recommendation.benchmarks:
            table.add_row(
                result.device,
                "ok" if result.error is None else "failed",
                "" if result.average_ms is None else f"{result.average_ms:.2f} ms",
            )
        console.print(table)


def main() -> None:
    if len(sys.argv) == 1:
        from ai_pc_kit.tui import run_tui

        run_tui()
        return

    app()


if __name__ == "__main__":
    main()
