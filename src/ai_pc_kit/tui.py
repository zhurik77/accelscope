from __future__ import annotations

import json
import os
import platform
import traceback
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Log,
    ProgressBar,
    Select,
    Static,
)

from ai_pc_kit.backends import list_backends
from ai_pc_kit.catalog import list_models
from ai_pc_kit.inspectors import AiPcReport, collect_report
from ai_pc_kit.model_zoo import download_model
from ai_pc_kit.reports import write_benchmark_report
from ai_pc_kit.runner import RunResult, compare_devices

REPORTS_DIR = Path("reports")
DEFAULT_DEVICES = ("CPU", "GPU", "NPU", "AUTO")


class AccelScopeApp(App[None]):
    """Textual TUI shell around the existing AccelScope commands."""

    CSS = """
    Screen {
        background: #101418;
        color: #e8edf2;
    }

    #layout {
        height: 1fr;
    }

    #sidebar {
        width: 27;
        background: #161c22;
        border-right: solid #2c3a44;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem.--highlight {
        background: #24405a;
    }

    #main {
        padding: 1 2;
        width: 1fr;
    }

    .card {
        border: solid #354653;
        padding: 1 2;
        margin-bottom: 1;
        background: #131a20;
    }

    #content {
        height: auto;
    }

    #table {
        height: 11;
        margin-bottom: 1;
    }

    #log {
        height: 9;
        border: solid #354653;
        margin-bottom: 1;
    }

    #benchmark-controls, #actions {
        height: auto;
        margin-bottom: 1;
    }

    Select {
        width: 24;
        margin-right: 1;
    }

    Button {
        margin-right: 1;
    }

    .hidden {
        display: none;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "dashboard", "Back"),
        ("r", "run", "Run"),
        ("e", "export", "Export"),
        ("d", "doctor", "Doctor"),
    ]

    NAV = (
        ("dashboard", "Dashboard"),
        ("hardware", "Inspect hardware"),
        ("devices", "OpenVINO devices"),
        ("benchmark", "Benchmark"),
        ("models", "Models"),
        ("backends", "Backends"),
        ("reports", "Reports"),
        ("doctor", "Doctor"),
        ("help", "Help"),
        ("exit", "Exit"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.current_section = "dashboard"
        self.report: AiPcReport | None = None
        self.last_results: list[RunResult] = []
        self.last_report_paths: list[Path] = []
        self.last_error: str | None = None
        self.benchmark_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="layout"):
            yield ListView(
                *[ListItem(Label(label), id=f"nav-{key}") for key, label in self.NAV],
                id="sidebar",
            )
            with Vertical(id="main"):
                yield Static("", id="status", classes="card")
                yield Static("", id="content", classes="card")
                yield DataTable(id="table")
                yield Log(id="log")
                yield ProgressBar(total=100, id="progress")
                with Horizontal(id="benchmark-controls"):
                    yield Select(
                        [(entry.key, entry.key) for entry in list_models()],
                        value="object-detection",
                        id="model-select",
                        prompt="Model",
                    )
                    yield Select(
                        [
                            ("All available devices", "ALL"),
                            *[(item, item) for item in DEFAULT_DEVICES],
                        ],
                        value="ALL",
                        id="device-select",
                        prompt="Device",
                    )
                    yield Select(
                        [("5", "5"), ("10", "10"), ("25", "25"), ("50", "50")],
                        value="10",
                        id="iterations-select",
                        prompt="Iterations",
                    )
                    yield Select(
                        [("Markdown", "md"), ("JSON", "json"), ("Both", "both")],
                        value="both",
                        id="format-select",
                        prompt="Export",
                    )
                with Horizontal(id="actions"):
                    yield Button("Refresh", id="refresh")
                    yield Button("Run benchmark", id="run-benchmark", variant="primary")
                    yield Button("Export", id="export", variant="success")
                    yield Button("Open reports", id="open-reports")
                    yield Button("Details", id="details")
                yield Static("", id="interpretation", classes="card")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "AccelScope"
        self.sub_title = "Benchmark first. Don't guess."
        self.query_one("#sidebar", ListView).index = 0
        self.show_dashboard()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        key = str(event.item.id or "").removeprefix("nav-")
        if key == "exit":
            self.exit()
            return
        self.show_section(key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "refresh":
            self.refresh_current()
        elif button_id == "run-benchmark":
            self.start_benchmark()
        elif button_id == "export":
            self.export_last_results()
        elif button_id == "open-reports":
            self.open_reports_folder()
        elif button_id == "details":
            self.show_details()

    def action_dashboard(self) -> None:
        self.show_section("dashboard")

    def action_run(self) -> None:
        if self.current_section == "benchmark":
            self.start_benchmark()
        elif self.current_section in {"hardware", "devices", "doctor"}:
            self.refresh_current()

    def action_export(self) -> None:
        self.export_last_results()

    def action_doctor(self) -> None:
        self.show_section("doctor")

    def show_section(self, key: str) -> None:
        self.current_section = key
        handler = getattr(self, f"show_{key}", None)
        if handler is None:
            self.show_dashboard()
            return
        handler()

    def set_status(self, extra: str = "") -> None:
        version = "0.1.0"
        ov_status = "unknown"
        if self.report:
            ov = self.report.openvino
            ov_status = ov.version or ("installed" if ov.installed else "missing")
        suffix = f"\n{extra}" if extra else ""
        self.query_one("#status", Static).update(
            f"[b]AccelScope {version}[/b]\n"
            f"OS: {platform.system()} {platform.release()} | Python: {platform.python_version()} | "
            f"OpenVINO: {ov_status}{suffix}"
        )

    def configure_view(
        self,
        *,
        table: bool = False,
        log: bool = False,
        benchmark_controls: bool = False,
        progress: bool = False,
        actions: Iterable[str] = (),
        interpretation: bool = False,
    ) -> None:
        self.query_one("#table", DataTable).set_class(not table, "hidden")
        self.query_one("#log", Log).set_class(not log, "hidden")
        self.query_one("#benchmark-controls", Horizontal).set_class(
            not benchmark_controls, "hidden"
        )
        self.query_one("#progress", ProgressBar).set_class(not progress, "hidden")
        self.query_one("#interpretation", Static).set_class(not interpretation, "hidden")
        action_ids = set(actions)
        for button in self.query("#actions Button"):
            button.set_class(button.id not in action_ids, "hidden")
        self.query_one("#actions", Horizontal).set_class(not action_ids, "hidden")

    def clear_table(self, *columns: str) -> DataTable:
        table = self.query_one("#table", DataTable)
        table.clear(columns=True)
        for column in columns:
            table.add_column(column)
        return table

    def clear_log(self) -> Log:
        log = self.query_one("#log", Log)
        log.clear()
        return log

    def show_dashboard(self) -> None:
        self.current_section = "dashboard"
        self.configure_view(
            actions=("refresh", "run-benchmark", "open-reports"), interpretation=True
        )
        self.set_status("Use arrows or mouse to move. Enter selects. Q quits.")
        if self.report is None:
            content = (
                "[b]Dashboard[/b]\n\n"
                "Run inspection to detect local AI hardware.\n\n"
                "Actions:\n"
                "- Refresh: inspect CPU, GPU, NPU, RAM, OS, Python and OpenVINO.\n"
                "- Run benchmark: compare CPU/GPU/NPU/AUTO on the default model.\n"
                "- Open reports: view exported benchmark files.\n\n"
                "Benchmark first. Don't guess."
            )
        else:
            content = self._report_summary(self.report)
        self.query_one("#content", Static).update(content)
        self.query_one("#interpretation", Static).update(
            "AccelScope is a reality check for AI PCs. It shows what local accelerator actually "
            "works and which path is faster on a real model."
        )

    def show_hardware(self) -> None:
        self.current_section = "hardware"
        self.configure_view(table=True, actions=("refresh", "export", "details"))
        self.set_status("Hardware inspection uses the same logic as `accelscope inspect`.")
        self.query_one("#content", Static).update(
            "[b]Hardware[/b]\nCPU, GPU, NPU, RAM, OS and Python."
        )
        self.refresh_hardware()

    def show_devices(self) -> None:
        self.current_section = "devices"
        self.configure_view(table=True, actions=("refresh", "details"))
        self.set_status(
            "Device visibility depends on drivers, runtime support and model compatibility."
        )
        self.query_one("#content", Static).update(
            "[b]OpenVINO devices[/b]\n"
            "NPU may exist in Device Manager but not be available to OpenVINO "
            "without the correct driver/runtime."
        )
        self.refresh_devices()

    def show_benchmark(self) -> None:
        self.current_section = "benchmark"
        self.configure_view(
            table=True,
            log=True,
            benchmark_controls=True,
            progress=True,
            actions=("run-benchmark", "export", "open-reports", "details"),
            interpretation=True,
        )
        self.set_status("Run a real model across CPU, GPU, NPU and AUTO.")
        self.query_one("#content", Static).update(
            "[b]Benchmark[/b]\nChoose a model, device set, iteration count and export format. "
            "The run happens in a background worker so the TUI stays responsive."
        )
        if not self.last_results:
            self.clear_table("Device", "Status", "Average latency", "Details")
            self.clear_log().write_line("Ready. Press R or click Run benchmark.")
            self.query_one("#interpretation", Static).update(
                "No benchmark has been run in this session."
            )

    def show_models(self) -> None:
        self.current_section = "models"
        self.configure_view(table=True, actions=("refresh", "open-reports"))
        self.set_status("Model templates are shared with `accelscope models list`.")
        self.query_one("#content", Static).update(
            "[b]Models[/b]\nBuilt-in task templates and download status."
        )
        table = self.clear_table("Key", "Backend", "Devices", "Status", "Notes")
        for entry in list_models():
            cached = self._model_cached(entry.key)
            table.add_row(
                entry.key,
                entry.backend,
                ", ".join(entry.recommended_devices),
                "cached" if cached else ("downloadable" if entry.download else "manual"),
                entry.notes,
            )

    def show_backends(self) -> None:
        self.current_section = "backends"
        self.configure_view(table=True)
        self.set_status("Current and planned backend paths. Planned means not implemented yet.")
        self.query_one("#content", Static).update(
            "[b]Backends[/b]\nOpenVINO is current. Others are roadmap."
        )
        table = self.clear_table("Backend", "Status", "Devices/providers", "Notes")
        for backend in list_backends():
            status = "available path" if backend.key == "openvino" else "planned"
            table.add_row(backend.key, status, ", ".join(backend.devices), backend.notes)

    def show_reports(self) -> None:
        self.current_section = "reports"
        self.configure_view(table=True, actions=("export", "open-reports"))
        self.set_status(f"Report folder: {REPORTS_DIR.resolve()}")
        self.query_one("#content", Static).update(
            "[b]Reports[/b]\nLatest Markdown and JSON reports plus a GitHub submission snippet."
        )
        table = self.clear_table("File", "Type", "Modified")
        REPORTS_DIR.mkdir(exist_ok=True)
        files = sorted(
            [*REPORTS_DIR.glob("*.md"), *REPORTS_DIR.glob("*.json")],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:10]
        for path in files:
            table.add_row(
                path.name,
                path.suffix.lstrip(".") or "file",
                datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            )
        self.query_one("#interpretation", Static).update(self.github_submission_snippet())

    def show_doctor(self) -> None:
        self.current_section = "doctor"
        self.configure_view(table=True, actions=("refresh", "details"))
        self.set_status("Doctor checks runtime visibility and gives the next useful command.")
        self.query_one("#content", Static).update(
            "[b]Doctor[/b]\nBasic diagnostics for local AI acceleration."
        )
        self.refresh_doctor()

    def show_help(self) -> None:
        self.current_section = "help"
        self.configure_view()
        self.set_status("Help")
        self.query_one("#content", Static).update(
            "[b]What AccelScope is[/b]\n"
            "AccelScope is a reality check for AI PCs. It shows what local "
            "accelerator actually works "
            "and which path is faster on a real model.\n\n"
            "[b]Recommended first flow[/b]\n"
            "1. Inspect hardware\n"
            "2. Show OpenVINO devices\n"
            "3. Run benchmark on all devices\n"
            "4. Export report\n"
            "5. Submit community benchmark result\n\n"
            "[b]Advanced CLI[/b]\n"
            "accelscope inspect\n"
            "accelscope devices\n"
            "accelscope benchmark object-detection --iterations 10 --output benchmark.md\n"
            "accelscope compare .\\models\\model.xml --devices CPU,GPU,NPU,AUTO\n"
            "accelscope models list\n"
            "accelscope backends list\n"
            "accelscope menu --classic\n\n"
            "Benchmark first. Don't guess."
        )

    def refresh_current(self) -> None:
        if self.current_section == "dashboard":
            self.refresh_hardware()
            self.show_dashboard()
        elif self.current_section == "hardware":
            self.refresh_hardware()
        elif self.current_section == "devices":
            self.refresh_devices()
        elif self.current_section == "doctor":
            self.refresh_doctor()
        elif self.current_section == "models":
            self.show_models()
        elif self.current_section == "reports":
            self.show_reports()

    def refresh_hardware(self) -> None:
        try:
            self.report = collect_report()
            self.last_error = None
            table = self.clear_table("Area", "Value", "Status")
            report = self.report
            table.add_row("OS", report.os, "ok")
            table.add_row("Python", report.python, "ok")
            table.add_row("RAM", f"{report.ram_gb} GB", "ok")
            table.add_row(
                "CPU",
                "unknown" if report.cpu is None else report.cpu.name or "unknown",
                "ok" if report.cpu else "unknown",
            )
            table.add_row(
                "GPU",
                "\n".join(gpu.name for gpu in report.gpus) or "none detected",
                "ok" if report.gpus else "missing",
            )
            table.add_row(
                "NPU",
                "\n".join(npu.name for npu in report.npus) or "none detected",
                "ok" if report.npus else "missing",
            )
            vendors = sorted({item.vendor for item in [*report.gpus, *report.npus] if item.vendor})
            table.add_row("Vendors", ", ".join(vendors) or "none detected", "info")
            self.set_status("Hardware refreshed.")
        except Exception as exc:
            self.show_error("Hardware inspection failed.", exc)

    def refresh_devices(self) -> None:
        try:
            self.report = collect_report(include_system=False)
            self.last_error = self.report.openvino.error
            devices = set(self.report.openvino.devices)
            table = self.clear_table("Device", "Status", "Notes")
            for device in DEFAULT_DEVICES:
                visible = device in devices or (device == "AUTO" and self.report.openvino.installed)
                note = "visible to OpenVINO" if visible else "not reported by runtime"
                table.add_row(device, "available" if visible else "unavailable", note)
            self.set_status("OpenVINO devices refreshed.")
        except Exception as exc:
            self.show_error("Device discovery failed.", exc)

    def refresh_doctor(self) -> None:
        try:
            self.report = collect_report()
            self.last_error = self.report.openvino.error
            report = self.report
            table = self.clear_table("Check", "Result", "Recommendation")
            table.add_row("OS", report.os, "ok")
            table.add_row("Python", report.python, "Use Python 3.10-3.12 for the OpenVINO path.")
            ov = report.openvino
            table.add_row(
                "OpenVINO",
                ov.version or ("missing" if not ov.installed else "installed"),
                "Install accelscope[openvino] if missing.",
            )
            table.add_row(
                "OpenVINO devices",
                ", ".join(ov.devices) or "none",
                "Run accelscope devices for raw runtime output.",
            )
            table.add_row(
                "CPU",
                report.cpu.name if report.cpu and report.cpu.name else "unknown",
                "CPU is the baseline.",
            )
            table.add_row(
                "GPU",
                ", ".join(gpu.name for gpu in report.gpus) or "none detected",
                "Always include GPU in comparison if present.",
            )
            table.add_row(
                "NPU",
                ", ".join(npu.name for npu in report.npus) or "none detected",
                "If not visible to OpenVINO, check NPU driver/runtime.",
            )
            table.add_row(
                "Model cache",
                "present" if Path("models").exists() else "empty",
                "Run accelscope benchmark object-detection.",
            )
            self.set_status(
                "Doctor complete. Next: accelscope benchmark object-detection --iterations 10"
            )
        except Exception as exc:
            self.show_error("Doctor failed.", exc)

    def start_benchmark(self) -> None:
        if self.benchmark_running:
            self.append_log("Benchmark is already running.")
            return
        self.show_benchmark()
        self.benchmark_running = True
        self.last_results = []
        self.last_report_paths = []
        self.clear_table("Device", "Status", "Average latency", "Details")
        self.clear_log().write_line("Starting benchmark worker...")
        self.set_progress(5)
        self.run_worker(self.run_benchmark_worker, thread=True, exclusive=True, exit_on_error=False)

    def run_benchmark_worker(self) -> None:
        try:
            model_key = str(
                self.call_from_thread(lambda: self.query_one("#model-select", Select).value)
            )
            device_value = str(
                self.call_from_thread(lambda: self.query_one("#device-select", Select).value)
            )
            iterations = int(
                str(
                    self.call_from_thread(
                        lambda: self.query_one("#iterations-select", Select).value
                    )
                )
            )
            fmt = str(self.call_from_thread(lambda: self.query_one("#format-select", Select).value))
            devices = list(DEFAULT_DEVICES if device_value == "ALL" else (device_value,))

            self.call_from_thread(self.append_log, f"Model: {model_key}")
            self.call_from_thread(self.append_log, f"Devices: {', '.join(devices)}")
            self.call_from_thread(self.append_log, "Downloading/checking model...")
            download = download_model(key=model_key, output_dir=Path("models"), convert=True)
            if download.model_xml is None:
                raise RuntimeError("No OpenVINO .xml model was found after download.")
            self.call_from_thread(self.set_progress, 35)
            self.call_from_thread(self.append_log, f"Model IR: {download.model_xml}")
            self.call_from_thread(self.append_log, "Running OpenVINO comparison...")
            results = compare_devices(
                model=download.model_xml,
                input_file=None,
                devices=devices,
                iterations=iterations,
            )
            self.call_from_thread(self.set_progress, 85)
            paths = self.write_reports(results, fmt)
            self.call_from_thread(self.finish_benchmark, results, paths)
        except Exception as exc:
            self.call_from_thread(self.show_error, "Benchmark failed.", exc)
            self.call_from_thread(self.set_progress, 0)
        finally:
            self.call_from_thread(self.set_benchmark_running, False)

    def write_reports(self, results: list[RunResult], fmt: str) -> list[Path]:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        paths: list[Path] = []
        if fmt in {"md", "both"}:
            path = REPORTS_DIR / f"benchmark-{stamp}.md"
            write_benchmark_report(path, results, fmt="md")
            write_benchmark_report(REPORTS_DIR / "benchmark-latest.md", results, fmt="md")
            paths.append(path)
        if fmt in {"json", "both"}:
            path = REPORTS_DIR / f"benchmark-{stamp}.json"
            write_benchmark_report(path, results, fmt="json")
            write_benchmark_report(REPORTS_DIR / "benchmark-latest.json", results, fmt="json")
            paths.append(path)
        return paths

    def finish_benchmark(self, results: list[RunResult], paths: list[Path]) -> None:
        self.last_results = results
        self.last_report_paths = paths
        self.populate_results_table(results)
        self.set_progress(100)
        for path in paths:
            self.append_log(f"Wrote report: {path}")
        self.query_one("#interpretation", Static).update(self.interpret_results(results))

    def set_benchmark_running(self, value: bool) -> None:
        self.benchmark_running = value

    def populate_results_table(self, results: list[RunResult]) -> None:
        table = self.clear_table("Device", "Status", "Average latency", "Details")
        for result in results:
            table.add_row(
                result.device,
                "ok" if result.error is None else "failed",
                "" if result.average_ms is None else f"{result.average_ms:.2f} ms",
                result.error or "",
            )

    def export_last_results(self) -> None:
        if self.current_section == "hardware" and self.report:
            REPORTS_DIR.mkdir(exist_ok=True)
            path = REPORTS_DIR / "hardware-latest.json"
            path.write_text(
                json.dumps(asdict(self.report), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.append_log(f"Wrote hardware report: {path}")
            return
        if not self.last_results:
            self.append_log("No benchmark results to export yet.")
            return
        fmt = str(self.query_one("#format-select", Select).value)
        self.last_report_paths = self.write_reports(self.last_results, fmt)
        for path in self.last_report_paths:
            self.append_log(f"Exported: {path}")

    def open_reports_folder(self) -> None:
        REPORTS_DIR.mkdir(exist_ok=True)
        try:
            os.startfile(REPORTS_DIR.resolve())  # type: ignore[attr-defined]
        except Exception as exc:
            self.show_error("Could not open reports folder.", exc)

    def show_details(self) -> None:
        detail = self.last_error or "No technical details captured."
        self.query_one("#content", Static).update(f"[b]Technical details[/b]\n{detail}")

    def show_error(self, title: str, exc: BaseException) -> None:
        self.last_error = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self.query_one("#content", Static).update(
            f"[b]{title}[/b]\n{exc}\n\nUse Details for technical output."
        )
        self.append_log(f"{title} {exc}")

    def append_log(self, line: str) -> None:
        self.query_one("#log", Log).write_line(line)

    def set_progress(self, value: float) -> None:
        bar = self.query_one("#progress", ProgressBar)
        bar.update(progress=value)

    def interpret_results(self, results: list[RunResult]) -> str:
        successful = [result for result in results if result.average_ms is not None]
        if not successful:
            return (
                "No successful device run. Check OpenVINO installation, drivers "
                "and model compatibility."
            )
        fastest = min(successful, key=lambda item: item.average_ms or float("inf"))
        slowest = max(successful, key=lambda item: item.average_ms or 0)
        lines = [
            f"Fastest path: {fastest.device} ({fastest.average_ms:.2f} ms).",
            f"Slowest successful path: {slowest.device} ({slowest.average_ms:.2f} ms).",
        ]
        gpu = next((item for item in successful if item.device == "GPU"), None)
        npu = next((item for item in successful if item.device == "NPU"), None)
        auto = next((item for item in successful if item.device == "AUTO"), None)
        if (
            gpu
            and npu
            and gpu.average_ms is not None
            and npu.average_ms is not None
            and gpu.average_ms < npu.average_ms
        ):
            lines.append(
                "On this model, GPU is faster than NPU. This is normal and is exactly why "
                "AccelScope compares devices instead of assuming NPU always wins."
            )
        if auto and auto.device != fastest.device and auto.average_ms != fastest.average_ms:
            lines.append("AUTO did not choose the fastest observed path in this run.")
        lines.append("Benchmark first. Don't guess.")
        return "\n".join(lines)

    def github_submission_snippet(self) -> str:
        report = self.report or collect_report()
        ov = report.openvino
        result_lines = []
        for result in self.last_results:
            latency = "failed" if result.average_ms is None else f"{result.average_ms:.2f} ms"
            result_lines.append(f"- {result.device}: {latency}")
        return (
            "[b]GitHub benchmark submission snippet[/b]\n"
            "- Laptop/device model: <fill in model>\n"
            f"- CPU: {report.cpu.name if report.cpu and report.cpu.name else '<fill in CPU>'}\n"
            f"- GPU: {', '.join(gpu.name for gpu in report.gpus) or '<fill in GPU>'}\n"
            f"- NPU: {', '.join(npu.name for npu in report.npus) or '<fill in NPU>'}\n"
            f"- RAM: {report.ram_gb} GB\n"
            f"- OS: {report.os}\n"
            f"- OpenVINO: {ov.version or ('missing' if not ov.installed else 'installed')}\n"
            "- AccelScope: 0.1.0\n"
            f"- Devices: {', '.join(ov.devices) or 'none'}\n"
            "- Benchmark result:\n"
            + ("\n".join(result_lines) if result_lines else "  <run benchmark first>")
        )

    def _report_summary(self, report: AiPcReport) -> str:
        cpu = report.cpu.name if report.cpu and report.cpu.name else "unknown"
        gpus = ", ".join(gpu.name for gpu in report.gpus) or "none detected"
        npus = ", ".join(npu.name for npu in report.npus) or "none detected"
        ov = report.openvino
        return (
            "[b]Dashboard[/b]\n\n"
            f"CPU: {cpu}\n"
            f"GPU: {gpus}\n"
            f"NPU: {npus}\n"
            f"RAM: {report.ram_gb} GB\n"
            f"OS: {report.os}\n"
            f"Python: {report.python}\n"
            f"OpenVINO: {ov.version or ('missing' if not ov.installed else 'installed')}\n"
            f"Detected devices: {', '.join(ov.devices) or 'none'}"
        )

    def _model_cached(self, key: str) -> bool:
        return (
            any(Path("models").rglob("*.xml"))
            if key in {"object-detection", "image-classification"}
            else False
        )


def run_tui() -> None:
    AccelScopeApp().run()
