# Development Roadmap

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Horizon:** 4 weeks to first validated baseline  
**Last updated:** 2026-06-19

---

## System Goal

Build a high-quality YOLO11 segmentation model for **wall, door, window** that outperforms `web_file` and `web2`.

---

## Phase Overview

| Week | Focus | Deliverable |
|------|-------|-------------|
| **1** | Annotation + export | Validated labels for 25-image batch |
| **2** | Training pipeline | `scripts/train.py`, first YOLO11 run |
| **3** | Evaluation + iteration | mAP report vs legacy; annotation fixes |
| **4** | Scale-up prep | Expand to 50+ images; harden QC |

---

## Week 1 — Annotation & Export

| Task | Owner | Output |
|------|-------|--------|
| CVAT setup (`IMPROVED_MODEL_1_Structural_Seg`) | Annotator | Project with 3 labels |
| Annotate ranks 1–25 (classes 0–2 only) | Annotator | CVAT polygons |
| Secondary review on val set (ranks 21–25) | Reviewer | QC sign-off |
| Export YOLO 1.1 seg + ID remap verify | ML | `labels/train/`, `labels/val/` |
| Create `dataset.yaml` | ML | `nc: 3`, proper split |
| Run `validate_labels.py` | ML | QC report ≥ 95% pass |

**Exit criteria:** 25 label files, 0 class-ID errors, val set reviewed.

---

## Week 2 — Training Pipeline

| Task | Owner | Output |
|------|-------|--------|
| Add `ultralytics` to project deps | ML | `requirements.txt` update (code task) |
| Implement `scripts/train.py` | ML | CLI training entry point |
| Implement `scripts/validate_labels.py` | ML | Pre-train gate |
| First YOLO11n-seg run (50 epochs, imgsz=1024) | ML | `runs/prototype/weights/best.pt` |
| Overlay inference on val set | ML | Visual QA images |

**Exit criteria:** Reproducible train command; checkpoint saved.

---

## Week 3 — Evaluation vs Legacy

| Task | Owner | Output |
|------|-------|--------|
| Implement `scripts/evaluate.py` | ML | Per-class mAP50 report |
| Train legacy baseline on same 20 train images (YOLOv8) | ML | Comparable checkpoint |
| Side-by-side val comparison | ML | Delta table (wall/door/window) |
| Fix annotation errors from failure cases | Annotator | Label patches |
| Retrain if val mAP below target | ML | Improved checkpoint |

**Exit criteria:** IMPROVED_MODEL_1 mAP50 ≥ legacy on ≥ 2 of 3 classes.

---

## Week 4 — Scale & Harden

| Task | Owner | Output |
|------|-------|--------|
| Annotate next 25 from `annotation_batch_01/` | Annotator | 50 total labeled |
| Implement `DatasetCleaner.create_splits()` | ML | Automated split manifests |
| Experiment log (MLflow or markdown) | ML | Run history |
| Document baseline results | ML | Update DATASET_AUDIT.md |
| ONNX export (optional) | ML | `best.onnx` |

**Exit criteria:** 50-image trained model; documented comparison vs legacy.

---

## Deferred (Not in Current Roadmap)

The following are explicitly **out of scope** until structural mAP beats legacy:

- Extended class taxonomies (11-class, 37-class)
- Room and furniture annotation
- Downstream mask-to-vector conversion
- Full-stack orchestration beyond training
- Web UI trainer parity with `web_file`

---

## Critical Path

```
CVAT annotation (0–2) → export → validate → train → evaluate vs legacy
```

**Current blocker:** Zero exported YOLO labels.

---

## Milestone Checklist

- [ ] 25 images annotated (classes 0–2)
- [ ] Labels exported and validated
- [ ] `dataset.yaml` with train ≠ val
- [ ] `scripts/train.py` runs YOLO11n-seg
- [ ] Val mAP50 reported per class
- [ ] Comparison vs `web_file` on same val set
- [ ] Annotation rulebook followed (no centerline walls, no room loops)

---

## Resource Estimate

| Role | Week 1 | Weeks 2–4 |
|------|--------|-----------|
| Annotator | 15–20 hrs | 10 hrs/week |
| ML Engineer | 5 hrs | 15 hrs/week |
| Reviewer | 3 hrs | 2 hrs/week |

---

*Roadmap v2 — YOLO11 segmentation training only.*
