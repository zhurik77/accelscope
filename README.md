# AccelScope

**AccelScope** is an AI PC capability profiler and model router for Windows laptops.

It answers two practical questions:

- What local AI hardware and runtimes does this machine actually expose?
- Which backend/device route should this model use: `CPU`, `GPU`, `NPU`, or `AUTO`?

```powershell
.\accelscope.exe
```

```text
AccelScope
Benchmark first. Don't guess.

[ Dashboard          ]  CPU / GPU / NPU summary
[ Inspect hardware   ]  Windows hardware inventory
[ Runtimes           ]  OpenVINO / ONNX Runtime / CUDA visibility
[ Model Inspector    ]  ONNX / OpenVINO IR metadata
[ Compatibility      ]  compile-test CPU / GPU / NPU / AUTO
[ Recommend          ]  suggested backend/device route
[ OpenVINO devices   ]  CPU / GPU / NPU / AUTO visibility
[ Benchmark          ]  model, device, iterations, export
[ Models             ]  known-good model templates
[ Backends           ]  current and planned runtimes
[ Reports            ]  Markdown / JSON benchmark exports
```

## Why

Modern laptops ship with AI accelerators, but it is still weirdly hard to answer simple questions:

- Is my NPU visible to the runtime?
- Is my integrated GPU faster than the NPU for this model?
- Which local backend should I try first?
- Can I export a benchmark report that other developers can compare?

AccelScope gives you a practical first answer from the terminal. It does not assume the NPU is
always fastest. It profiles the machine, checks runtime visibility, inspects the model, tests
compatibility, and can export a routing manifest for your app.

Core message: **Benchmark first. Don't guess.**

## Current Focus

The first working path targets Intel Core Ultra systems with:

- Intel Arc integrated GPU
- Intel AI Boost NPU
- OpenVINO

The project is not Intel-only. The backend roadmap includes ONNX Runtime, DirectML, CUDA, and ROCm.

## Quick Start

Download `accelscope.exe` from the latest release, then run:

```powershell
.\accelscope.exe
```

That opens the Textual terminal UI by default. The same UI is available from source:

```powershell
accelscope
accelscope tui
```

Or run from source:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[openvino]"
accelscope
```

The fastest non-interactive benchmark:

```powershell
accelscope benchmark object-detection --iterations 10 --output benchmark.md
```

Inspect a model and produce a route recommendation:

```powershell
accelscope inspect-model .\models\model.xml
accelscope compatibility .\models\model.xml
accelscope recommend .\models\model.xml --benchmark --iterations 5
accelscope route .\models\model.xml --output accelscope.routing.json
```

## Example Result

From the first test laptop:

| Hardware | Value |
| --- | --- |
| CPU | Intel Core Ultra 5 125H |
| GPU | Intel Arc integrated graphics |
| NPU | Intel AI Boost |
| RAM | 24 GB |

| Device | Average latency |
| --- | ---: |
| CPU | 13.22 ms |
| GPU | 4.05 ms |
| NPU | 9.81 ms |
| AUTO | 16.62 ms |

The useful signal is not "NPU always wins". It is seeing which local path wins for a real model on a
real machine.

## Commands

Interactive TUI:

```powershell
accelscope
accelscope tui
```

Legacy number menu:

```powershell
accelscope menu --classic
```

Inspect hardware:

```powershell
accelscope inspect
```

Show OpenVINO devices:

```powershell
accelscope devices
```

Run diagnostics:

```powershell
accelscope doctor
```

Scan normalized hardware capabilities:

```powershell
accelscope profile
accelscope profile --json
```

Scan runtimes/providers:

```powershell
accelscope runtimes
accelscope runtimes --json
```

Inspect model metadata:

```powershell
accelscope inspect-model .\models\model.onnx
accelscope inspect-model .\models\model.xml --json
```

Test model compatibility:

```powershell
accelscope compatibility .\models\model.xml
```

Recommend and export a route:

```powershell
accelscope recommend .\models\model.xml --benchmark --iterations 5
accelscope route .\models\model.xml --output accelscope.routing.json
```

Download and benchmark the default model:

```powershell
accelscope benchmark object-detection --iterations 10 --output benchmark.md
```

Compare your own OpenVINO IR model:

```powershell
accelscope compare .\models\model.xml --devices CPU,GPU,NPU,AUTO --iterations 50
```

Export JSON:

```powershell
accelscope compare .\models\model.xml --json
```

Browse model templates and backend plans:

```powershell
accelscope models list
accelscope backends list
```

The legacy alias also works:

```powershell
ai-pc inspect
```

## Build Windows exe

Inspector-only build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -Clean
```

OpenVINO + Open Model Zoo build:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -e ".[dev,openvino]" openvino-dev==2024.6.0
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -Clean -PythonExe .\.venv312\Scripts\python.exe -IncludeOpenVINO -IncludeOMZ
```

See [docs/BUILD.md](docs/BUILD.md).

## Project Docs

- [Quickstart](docs/QUICKSTART.md)
- [Textual TUI](docs/TUI.md)
- [Capability profiler](docs/CAPABILITY_PROFILER.md)
- [Model inspector](docs/MODEL_INSPECTOR.md)
- [Recommendation engine](docs/RECOMMENDATION_ENGINE.md)
- [Routing manifest](docs/ROUTING_MANIFEST.md)
- [Model packs](docs/MODEL_PACKS.md)
- [Build](docs/BUILD.md)
- [Product shape](docs/PRODUCT.md)
- [Example benchmark](examples/benchmark-intel-core-ultra-5-125h.md)
- [Community benchmarks](docs/COMMUNITY_BENCHMARKS.md)

## Roadmap

- ONNX Runtime provider discovery and runner
- DirectML smoke tests for Windows GPUs
- More known-good benchmark models
- Model packs for vision, office AI, creator, and developer workflows
- Community benchmark table through pull requests
- HTML report output
- Optional MCP tools for local OCR, embeddings, and vision tasks

## Contributing

Benchmark reports from real hardware are very welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
