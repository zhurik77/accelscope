# Model Inspector

Use:

```powershell
accelscope inspect-model .\models\model.onnx
accelscope inspect-model .\models\model.xml --json
```

Supported first formats:

- `.onnx`
- OpenVINO IR `.xml` with a neighboring `.bin`

For ONNX, AccelScope uses the optional `onnx` package when available. If it is missing, the command
returns a friendly install hint instead of failing with a traceback.

Collected fields include model size, opset, graph inputs/outputs, node count, operator type counts,
initializer precision hints, and dynamic/static shape hints where possible.

For OpenVINO IR, AccelScope checks XML/BIN presence and uses OpenVINO to read input/output shapes and
element types.

## Task Guess

The inspector includes a conservative task classifier:

- object-detection
- image-classification
- segmentation
- embeddings
- OCR
- speech
- unknown

Each guess includes a confidence score and signals. AccelScope should not overclaim; weak evidence
stays `unknown` or low-confidence.
