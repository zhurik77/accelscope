# Model Packs

Model packs are planned collections of known-good models that make AccelScope useful immediately
after download.

Each pack should define:

- purpose
- models
- source
- expected format
- recommended devices
- known limitations
- download/cache behavior

## Vision Pack

Purpose: quick local vision diagnostics and demos.

First working model:

- `object-detection`
- Source: Open Model Zoo `person-detection-retail-0013`
- Expected format: OpenVINO IR
- Recommended devices: GPU, NPU, AUTO, CPU
- Cache behavior: downloaded under `models/`
- Known limitations: one compact object detection model does not represent every vision workload

## Office AI Pack

Purpose: document OCR, screenshot understanding, and privacy-friendly local office workflows.

Status: planned.

## Creator Pack

Purpose: media and creator-oriented models such as segmentation or enhancement.

Status: planned.

## Developer Pack

Purpose: embeddings, semantic code search, and local RAG building blocks.

Status: planned.
