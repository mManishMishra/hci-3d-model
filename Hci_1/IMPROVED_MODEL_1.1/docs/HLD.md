# High-Level Design (HLD)

**Project:** IMPROVED_MODEL_1 — YOLO11 7-Class Segmentation Training  
**Version:** 3.0  
**Date:** 2026-06-19

---

## Purpose

Train a **YOLO11 instance-segmentation** model on **7 floor-plan classes** that outperforms legacy `web_file` / `web2`.

### Locked classes (IDs 0–6)

wall, door, window, bedroom, living_room, kitchen, bathroom

**Config:** `data/prototype_7_classes.yaml`  
**Batch:** `data/prototype_7_batch/`

---

## Pipeline

```
CVAT (7 polygon labels)
  → export_cvat_to_yolo.py
  → validate_labels.py
  → check_dataset_integrity.py
  → train.py (YOLO11n-seg)
  → evaluate.py
```

---

## Success criteria

| ID | Criterion |
|----|-----------|
| M1 | 25 images annotated (classes 0–6) |
| M2 | Labels validated; train ≠ val |
| M3 | YOLO11 checkpoint trained |
| M4 | Val mAP50 beats legacy on shared classes |

---

## Implementation status

| Component | Status |
|-----------|--------|
| `prototype_7_batch/` layout | ✅ |
| `dataset.yaml` | ✅ |
| Label validation scripts | ✅ |
| `train.py` / `evaluate.py` | ✅ (needs labels + working torch) |
| Exported labels | ⏳ Pending CVAT |

---

## Out of scope

Modules in `src/_deferred/` are not part of this HLD.

---

*HLD v3 — 7-class segmentation training.*
