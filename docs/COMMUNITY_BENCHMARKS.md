# Community Benchmarks

This page is meant to grow through pull requests.

Run:

```powershell
accelscope benchmark object-detection --iterations 10 --output benchmark.md
```

Then submit your result with the hardware details.

## Results

| CPU | GPU | NPU | OS | CPU ms | GPU ms | NPU ms | AUTO ms | Notes |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Intel Core Ultra 5 125H | Intel Arc integrated | Intel AI Boost | Windows 11 | 13.22 | 4.05 | 9.81 | 16.62 | First test laptop |

## Why Results Can Differ

Latency depends on drivers, power mode, thermal state, precision, model operators, runtime version,
and whether the device has already warmed up. AccelScope is not trying to produce a universal score.
It is trying to make local execution paths visible and comparable on the same machine.
