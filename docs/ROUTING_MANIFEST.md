# Routing Manifest

Use:

```powershell
accelscope route .\models\model.xml --output accelscope.routing.json
```

The routing manifest is intended for developers who want to route local AI workloads in their own
apps without rediscovering the machine from scratch.

Shape:

```json
{
  "model": {
    "path": "...",
    "format": "onnx",
    "task_guess": "object-detection",
    "opset": 17
  },
  "machine": {
    "cpu": "...",
    "gpus": [],
    "npus": [],
    "ram_gb": 24,
    "os": "Windows 11"
  },
  "recommendation": {
    "best_default": {
      "backend": "openvino",
      "device": "GPU"
    },
    "fallback": {
      "backend": "openvino",
      "device": "CPU"
    },
    "avoid": [],
    "confidence": 0.82
  },
  "benchmarks": [],
  "compatibility": []
}
```

The manifest is deliberately JSON-first and stable enough to be checked into bug reports, benchmark
submissions, or app-specific routing configs.
