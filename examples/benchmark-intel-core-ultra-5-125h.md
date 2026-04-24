# Benchmark: Intel Core Ultra 5 125H

First AccelScope test machine.

## Hardware

| Component | Value |
| --- | --- |
| CPU | Intel Core Ultra 5 125H |
| GPU | Intel Arc integrated graphics |
| NPU | Intel AI Boost |
| RAM | 24 GB |
| OS | Windows 11 |
| Runtime | OpenVINO 2024.6 |

## Model

| Field | Value |
| --- | --- |
| Task | Object detection |
| Model | `person-detection-retail-0013` |
| Source | OpenVINO Open Model Zoo |

## Result

| Device | Status | Average latency |
| --- | --- | ---: |
| CPU | ok | 13.22 ms |
| GPU | ok | 4.05 ms |
| NPU | ok | 9.81 ms |
| AUTO | ok | 16.62 ms |

## Notes

On this model, the integrated GPU is faster than the NPU. That is exactly why AccelScope compares
all local execution paths instead of assuming one accelerator always wins.
