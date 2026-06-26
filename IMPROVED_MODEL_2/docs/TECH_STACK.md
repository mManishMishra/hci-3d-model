# Technology Stack

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19

---

## System Goal

YOLO11 instance segmentation for floor-plan **wall, door, window** — training pipeline that beats legacy `web_file` / `web2`.

---

## Core Stack

| Layer | Technology | Version | Role |
|-------|------------|---------|------|
| Language | Python | 3.11 | All tooling |
| Segmentation framework | **Ultralytics YOLO11** | ≥8.3 | Train + infer |
| Base weights | `yolo11n-seg.pt` | — | Prototype model |
| Annotation | **CVAT** (Docker) | Latest stable | Polygon labeling |
| Export format | YOLO 1.1 segmentation | — | Ultralytics-compatible |
| Image I/O | OpenCV, Pillow | 4.8+, 10+ | Preprocess + overlay |
| Config | YAML | — | `dataset.yaml`, class defs |
| Testing | pytest | ≥7.4 | Unit tests |

---

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `model` | `yolo11n-seg.pt` | Fast iteration on small dataset |
| `imgsz` | **1024** | Preserve thin wall lines (legacy used 640) |
| `epochs` | 50 | Small dataset |
| `batch` | 4 | 8 GB VRAM typical |
| `mosaic` | 1.0 | Critical for 20 train images |
| `degrees` | 5.0 | Mild rotation aug |
| `fliplr` | 0.5 | Orientation variance |
| `patience` | 15 | Early stopping |

---

## Annotation Stack

| Tool | Purpose |
|------|---------|
| CVAT (local Docker) | Polygon annotation |
| Project name | `IMPROVED_MODEL_1_Structural_Seg` |
| Labels | wall, door, window (polygon only) |
| Export | YOLO 1.1 segmentation |
| Draft helper | `scripts/cursor_draft_annotator.py` (not GT) |

---

## Dataset Tooling

| Component | Path | Status |
|-----------|------|--------|
| Dataset cleaner | `src/dataset_tools/dataset_cleaner.py` | Partial |
| Batch prep | `scripts/prepare_prototype_11_batch.py` | Done |
| Label validator | `scripts/validate_labels.py` | Planned |
| Class config | `data/prototype_classes.yaml` | Done (`nc: 3`) |

---

## Evaluation Stack

| Metric | Tool |
|--------|------|
| mask mAP50 | Ultralytics `model.val()` |
| Per-class breakdown | Custom `evaluate.py` |
| Legacy comparison | Same val set, `web_file` weights |
| Visual QA | OpenCV overlay on val images |

---

## Development Dependencies

```text
# Training (add when implementing scripts/train.py)
ultralytics>=8.3

# Already in project
pydantic>=2.5
pyyaml>=6.0
numpy>=1.24
opencv-python-headless>=4.8
pillow>=10.0

# Dev
pytest>=7.4
ruff>=0.3
```

---

## Hardware Recommendations

| Task | Minimum | Recommended |
|------|---------|-------------|
| Annotation | Any laptop | 1080p+ display for CVAT |
| YOLO11n training | CPU (slow) | NVIDIA RTX 3070+ 8GB |
| YOLO11s/m (future) | RTX 3080 10GB | RTX 4090 24GB |

---

## Legacy Comparison

| | `web_file` / `web2` | IMPROVED_MODEL_1 |
|---|---------------------|------------------|
| Framework | Ultralytics YOLOv8-seg | **YOLO11-seg** |
| Classes | 17 (incl. Room) | **3** (wall, door, window) |
| Annotation | Broken mock detector | **CVAT human polygons** |
| imgsz | 640 default | **1024** |
| Val split | train=val=test | **20/5 proper split** |

---

## Explicitly Not in Stack (Deferred)

The following are **not required** for the current training milestone:

- IfcOpenShell
- NetworkX / Shapely (for training path)
- LLM APIs (Gemini, etc.)
- 3D viewers
- Graph databases

Existing stub modules in `src/` that reference deferred technologies must not block training delivery.

---

## Version Pinning Policy

- Pin `ultralytics` minor version once first successful train completes
- Record exact versions in training run metadata
- Reproducibility: fix random seed in train script when implemented

---

*TECH_STACK v2 — segmentation training scope only.*
