# Product Shape

AccelScope combines two related tools:

1. **Capability Inspector**: prove what hardware and runtimes are available.
2. **Model Runner**: run and compare models across CPU, GPU, NPU, and AUTO.

The public promise is simple: "Run one command and understand what your local AI hardware can
actually do."

## First-Class Devices

The project treats GPU and NPU as separate execution targets:

- **CPU**: compatibility baseline and fallback path.
- **GPU**: preferred path for many heavier models on Intel Arc integrated graphics.
- **NPU**: efficient path for supported compact models and background inference.
- **AUTO**: OpenVINO-managed selection.

This matters because local AI development is not a single-vendor or single-device story. Useful apps
should be able to pick a backend/device based on latency, throughput, battery usage, operator
support, and driver availability.

## Backend Strategy

OpenVINO is the first implemented runner because it fits the current test laptop well. The broader
shape is intentionally multi-backend:

- **OpenVINO**: CPU/GPU/NPU/AUTO, best first path for Intel AI PCs.
- **ONNX Runtime**: portable ONNX path with CPU, DirectML, CUDA, and other execution providers.
- **DirectML**: Windows GPU acceleration across vendors where drivers support it.
- **CUDA**: NVIDIA path for heavier local workloads.
- **ROCm**: AMD path, especially on Linux workstations.

## Launch Variants

### CLI

The first launch target. Best for developers, GitHub users, bug reports, and benchmarks.

```powershell
accelscope
accelscope inspect
accelscope devices
accelscope benchmark object-detection
accelscope compare .\models\model.xml --devices CPU,GPU,NPU,AUTO
accelscope backends list
```

When launched without arguments, the CLI opens an interactive prompt:

```text
1. Inspect hardware
2. Show OpenVINO devices
3. Run benchmark
0. Exit
```

### JSON Report

Useful for GitHub issues, reproducible benchmark submissions, and automatic diagnostics.

```powershell
accelscope inspect --json
```

### Python Library

Useful for notebooks, internal tools, and integration into other projects.

```python
from ai_pc_kit.inspectors import collect_report

report = collect_report()
print(report.openvino.devices)
```

### Local API

Future target. A small HTTP server can expose inspection and runner features to desktop apps.

```text
GET  /devices
POST /benchmark
POST /run
```

### Desktop App

Future target. A Tauri or Electron UI can make the same features accessible to non-CLI users:

- hardware dashboard;
- model catalog;
- benchmark history;
- device comparison charts;
- exportable reports.

### MCP Server

Future target. Local AI tools can be exposed to coding agents:

- inspect local AI hardware;
- benchmark a model;
- run embeddings;
- run OCR;
- run image classification.

## GitHub Star Hooks

- "Does my NPU work?" one-command answer.
- CPU vs GPU vs NPU reports for real laptops.
- OpenVINO model catalog with copy-paste commands.
- Community benchmark table through pull requests.
- MCP tools for local Intel AI PC inference.

## Near-Term MVP

1. Improve benchmark caching and model reuse.
2. Add ONNX Runtime provider discovery.
3. Add DirectML smoke tests.
4. Add a public community benchmark table.
5. Publish initial GitHub repository and ask for benchmark PRs from other local AI hardware owners.
