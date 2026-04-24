# AccelScope TUI

AccelScope opens a Textual-based terminal UI by default:

```powershell
accelscope
accelscope tui
.\dist\accelscope.exe
```

The UI is designed to feel like a small diagnostic app inside the terminal. Use arrow keys or the
mouse to move through the sidebar, Enter to select, Esc to return to Dashboard, R to run the current
screen action, E to export, D for Doctor, and Q to quit.

## Screens

- Dashboard: CPU, GPU, NPU, RAM, OS, Python, OpenVINO status, and detected runtime devices.
- Inspect hardware: reuses `accelscope inspect` logic and can export `reports/hardware-latest.json`.
- Runtimes: scans OpenVINO, optional ONNX Runtime providers, CUDA detection and planned runtimes.
- OpenVINO devices: shows CPU, GPU, NPU and AUTO visibility from the OpenVINO runtime.
- Benchmark: downloads/checks a known-good model, compares devices, streams logs, shows progress,
  and exports Markdown/JSON reports.
- Model Inspector: accepts a model path and inspects ONNX/OpenVINO IR metadata.
- Compatibility: accepts a model path and compile-tests OpenVINO CPU/GPU/NPU/AUTO.
- Recommend: accepts a model path and produces a backend/device route recommendation.
- Models: lists built-in model templates and cache status.
- Backends: shows OpenVINO as the current path and labels ONNX Runtime, DirectML, CUDA and ROCm as
  planned unless implemented.
- Reports: lists recent reports and produces a GitHub benchmark submission snippet.
- Doctor: summarizes OS, Python, OpenVINO, devices, hardware detection and next commands.
- Help: recommended first flow and advanced CLI commands.

## Benchmark Flow

1. Open `Benchmark`.
2. Choose a model template, usually `object-detection`.
3. Choose `All available devices` to compare CPU, GPU, NPU and AUTO.
4. Pick 10, 25 or 50 iterations.
5. Choose Markdown, JSON or Both.
6. Press `R` or click `Run benchmark`.

Reports are written under `reports/` so they stay outside PyInstaller's temporary extraction
directory. The latest files are also mirrored as `benchmark-latest.md` and `benchmark-latest.json`.

## Troubleshooting

- If OpenVINO is missing, install `accelscope[openvino]` or use the bundled release exe.
- If NPU appears in Device Manager but not in AccelScope, the OpenVINO runtime may not see the NPU
  plugin. Check Intel NPU drivers and OpenVINO runtime support.
- If a model fails on one device, keep the other device results. Model/operator compatibility can
  differ between CPU, GPU, NPU and AUTO.
- If the TUI is not usable in a particular terminal, run `accelscope menu --classic` for the legacy
  number-based fallback.

AccelScope is a reality check for AI PCs. It shows what local accelerator actually works and which
path is faster on a real model.

Benchmark first. Don't guess.
