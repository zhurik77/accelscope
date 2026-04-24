# Quickstart

Start interactive mode:

```powershell
.\dist\accelscope.exe
```

Then choose:

```text
1. Inspect hardware
2. Show OpenVINO devices
3. Run benchmark
0. Exit
```

Run the fastest one-command check:

```powershell
.\dist\accelscope.exe benchmark object-detection --iterations 10 --output benchmark.md
```

This command:

- downloads a known-good OpenVINO object detection model;
- checks `CPU`, `GPU`, `NPU`, and `AUTO`;
- writes a Markdown benchmark report.

Useful separate commands:

```powershell
.\dist\accelscope.exe inspect
.\dist\accelscope.exe devices
.\dist\accelscope.exe backends list
.\dist\accelscope.exe models list
```

Example result from the first test laptop:

| Device | Average latency |
| --- | ---: |
| CPU | 12.68 ms |
| GPU | 5.70 ms |
| NPU | 16.01 ms |
| AUTO | 27.36 ms |

Hardware:

- Intel Core Ultra 5 125H
- Intel Arc integrated graphics
- Intel AI Boost NPU
- 24 GB RAM

The exact numbers will vary between runs. The important signal is whether each local execution path
works and how it behaves on the same model.
