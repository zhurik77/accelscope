# Recommendation Engine

Use:

```powershell
accelscope recommend .\models\model.xml
accelscope recommend .\models\model.xml --benchmark --iterations 5
```

The recommendation engine combines:

- hardware capability profile
- runtime capability profile
- model inspection
- OpenVINO compatibility checks
- optional short benchmark observations

It produces:

- best_default
- best_latency
- best_compatibility
- best_battery_candidate
- fallback
- avoid
- confidence

Confidence is higher when the model is inspected successfully, at least one device compiles, and a
short benchmark succeeds. Without a benchmark, recommendations are still useful but more conservative.

AccelScope does not assume NPU is fastest. GPU may beat NPU on a given model, and AUTO may be slower
than an explicit route. That is the point of the tool.
