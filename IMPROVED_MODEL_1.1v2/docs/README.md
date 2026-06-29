# IMPROVED_MODEL_1 — Documentation Index

**Project:** YOLO11 7-class floor-plan segmentation training  
**Active batch:** `data/prototype_7_batch/`  
**Active config:** `data/prototype_7_classes.yaml`

---

## Current phase

**ANNOTATION → DATASET BUILD → FIRST TRAINING RUN**

---

## Essential documents

| Document | Purpose |
|----------|---------|
| **[01_PROJECT_TRAINING_SYSTEM_GUIDE.md](./01_PROJECT_TRAINING_SYSTEM_GUIDE.md)** | **SINGLE SOURCE OF TRUTH** — complete training ecosystem onboarding manual |
| [COMPLETE_WORKFLOW.md](./COMPLETE_WORKFLOW.md) | **Full end-to-end workflow** — IMPROVED_MODEL_1 vs legacy |
| [CVAT_OVERVIEW.md](./CVAT_OVERVIEW.md) | **What is CVAT** — stakeholder guide (share with senior) |
| [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) | **Authoritative** 7-class annotation rules |
| [ANNOTATION_EXECUTION_PLAN.md](./ANNOTATION_EXECUTION_PLAN.md) | Step-by-step CVAT workflow |
| [PROTOTYPE_ANNOTATION_GUIDE.md](./PROTOTYPE_ANNOTATION_GUIDE.md) | Annotator quick guide |
| [HLD.md](./HLD.md) | Training system architecture |
| [LLD.md](./LLD.md) | Module interfaces |
| [DEVELOPMENT_ROADMAP.md](./DEVELOPMENT_ROADMAP.md) | Delivery phases |

---

## Locked 7-class taxonomy

| ID | Class |
|----|-------|
| 0 | wall |
| 1 | door |
| 2 | window |
| 3 | bedroom |
| 4 | living_room |
| 5 | kitchen |
| 6 | bathroom |

---

## Pipeline

```
CVAT → export_cvat_to_yolo.py → validate_labels.py → check_dataset_integrity.py → train.py → evaluate.py
```

---

## Deprecated references

- 3-class configs (`prototype_classes.yaml`) — do not use
- 11-class configs (`prototype_11_classes.yaml`) — do not use
- `src/_deferred/` — not part of training pipeline

---

*Documentation aligned to 7-class YOLO11 segmentation — 2026-06-19.*
