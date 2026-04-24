# AccelScope

**AccelScope** is a menu-first CLI for discovering and benchmarking local AI hardware.

Open it, pick a number, and see what your machine can actually run across `CPU`, `GPU`, `NPU`, and
runtime backends.

```powershell
.\dist\accelscope.exe
```

```text
1. Inspect hardware
2. Show OpenVINO devices
3. Run benchmark
4. Show model templates
5. Show backends
6. Help
0. Exit
```

## Why

Modern laptops ship with AI accelerators, but it is still weirdly hard to answer simple questions:

- Is my NPU visible to the runtime?
- Is my integrated GPU faster than the NPU for this model?
- Which local backend should I try first?
- Can I export a benchmark report that other developers can compare?

AccelScope gives you a practical first answer from the terminal.

## Current Focus

The first working path targets Intel Core Ultra systems with:

- Intel Arc integrated GPU
- Intel AI Boost NPU
- OpenVINO

The project is not Intel-only. The backend roadmap includes ONNX Runtime, DirectML, CUDA, and ROCm.

## Quick Start

Use the packaged exe:

```powershell
.\dist\accelscope.exe
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

Interactive menu:

```powershell
accelscope
```

Inspect hardware:

```powershell
accelscope inspect
```

Show OpenVINO devices:

```powershell
accelscope devices
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
- [Build](docs/BUILD.md)
- [Product shape](docs/PRODUCT.md)
- [Example benchmark](examples/benchmark-intel-core-ultra-5-125h.md)
- [Community benchmarks](docs/COMMUNITY_BENCHMARKS.md)

## Roadmap

- ONNX Runtime provider discovery and runner
- DirectML smoke tests for Windows GPUs
- More known-good benchmark models
- Community benchmark table through pull requests
- HTML report output
- Optional MCP tools for local OCR, embeddings, and vision tasks

## Contributing

Benchmark reports from real hardware are very welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
