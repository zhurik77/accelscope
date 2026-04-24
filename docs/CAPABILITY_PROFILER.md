# Capability Profiler

AccelScope now has a normalized hardware capability object:

```json
{
  "system": {},
  "cpu": {},
  "gpus": [],
  "npus": [],
  "memory": {},
  "warnings": []
}
```

Use:

```powershell
accelscope profile
accelscope profile --json
```

The profiler collects OS, Windows build, architecture, Python and AccelScope version, power/battery
status when available, CPU cores and instruction hints, GPU/NPU inventory, and memory totals.

Fields are best-effort. If a field is not reliable on the current machine, AccelScope returns
`null`, `unknown`, or a warning instead of inventing a value.

## Runtime Profile

Use:

```powershell
accelscope runtimes
accelscope runtimes --json
```

Current stable runtime:

- OpenVINO: installed/version/devices through `openvino.Core`

Optional or detection-only runtimes:

- ONNX Runtime: import/version/providers when installed
- CUDA: detection-only through `nvcuda.dll`
- DirectML, TensorRT, ROCm, Qualcomm QNN: planned or detection-only placeholders

Runtime scanning must never require optional dependencies just to run.
