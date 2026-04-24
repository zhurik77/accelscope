# Contributing

Thanks for helping make AccelScope useful on real machines.

## Useful Contributions

- Benchmark results from laptops and desktops.
- Bug reports for missing GPU/NPU/runtime detection.
- New known-good model templates.
- Backend integrations: ONNX Runtime, DirectML, CUDA, ROCm.
- Packaging improvements for Windows.

## Local Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,openvino]"
python -m pytest
```

## Submit A Benchmark

Run:

```powershell
accelscope benchmark object-detection --iterations 10 --output benchmark.md
```

Then open an issue or PR with:

- CPU model
- GPU model
- NPU model, if present
- RAM
- OS
- AccelScope version or commit
- benchmark table

## Development Notes

- Keep the menu-first flow simple.
- Keep non-interactive commands scriptable.
- Do not assume NPU is always faster than GPU.
- Treat failures as useful signal when a runtime cannot compile a model.
