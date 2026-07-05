# Folder Structure — Training Scope

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19

---

## System Goal

Directory layout for dataset → annotation → training → evaluation pipeline.

---

## Active Structure

```
IMPROVED_MODEL_1/
├── data/
│   ├── prototype_classes.yaml       # nc: 3 — ACTIVE training config
│   ├── prototype_11_classes.yaml    # DEFERRED — 11-class reference only
│   ├── prototype_11_batch/          # ACTIVE annotation batch
│   │   ├── images/                  # 25 JPGs (+ train/val subdirs at export)
│   │   ├── labels/                  # CREATE at export: train/, val/
│   │   ├── manifest.csv             # Rank → split assignment
│   │   ├── selection.json
│   │   └── dataset.yaml             # CREATE at export
│   ├── prototype_dataset/           # Smaller pilot batch (13 images)
│   ├── annotation_batch_01/       # Phase 2 pool (50 images)
│   └── dataset_clean/               # Deduplicated corpus (when built)
│
├── docs/                            # Design docs (this folder)
│   ├── CANONICAL_ANNOTATION_RULEBOOK.md
│   ├── HLD.md
│   ├── LLD.md
│   └── ...
│
├── scripts/
│   ├── prepare_prototype_11_batch.py
│   ├── setup_prototype_dataset.py
│   ├── clean_dataset.py
│   ├── cursor_draft_annotator.py    # Draft helper — not GT
│   ├── train.py                     # PLANNED
│   ├── validate_labels.py           # PLANNED
│   └── evaluate.py                  # PLANNED
│
├── src/
│   ├── preprocessing/               # ACTIVE — image preprocessor
│   ├── dataset_tools/               # ACTIVE — cleaner, audit (partial)
│   └── tests/                       # Unit tests
│
├── runs/                            # Training outputs (Ultralytics)
│   └── prototype/
│       └── weights/
│           └── best.pt
│
├── outputs/                         # Preprocess debug artifacts
├── pyproject.toml
└── requirements.txt
```

---

## Key Paths

| Path | Purpose |
|------|---------|
| `data/prototype_11_batch/images/` | Active 25-image batch |
| `data/prototype_11_batch/labels/train/` | Training labels (create on export) |
| `data/prototype_11_batch/labels/val/` | Validation labels (create on export) |
| `data/prototype_classes.yaml` | 3-class YOLO config |
| `runs/prototype/weights/best.pt` | Trained checkpoint (future) |

---

## Deferred / Out of Scope Paths

The following directories exist or are planned in code stubs but are **not part of the current training milestone documentation:**

```
src/graph_builder/          # Stub — deferred
src/topology_validator/     # Stub — deferred
src/bim_schema/             # Stub — deferred
src/ifc_adapter/            # Stub — deferred
src/pipeline/               # Full-stack stub — deferred
src/detection/              # Not created — planned for inference post-train
src/training/               # Not created — planned
```

Do not prioritize these paths until structural segmentation beats legacy.

---

## Legacy Reference (Read-Only)

```
web_file/
├── web/server.py             # Baseline trainer patterns
├── web/auto_label.py         # contour_to_yolo_seg format reference
├── config/classes.py         # 17-class legacy taxonomy
└── logic/detector.py         # Mock — do not replicate

web 2/web/
└── server.py                 # Extended fork — not runnable standalone
```

---

## Dataset Layout Standard (YOLO)

```
{batch_root}/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/    # {stem}.txt per image
│   └── val/
└── dataset.yaml
```

**Rule:** `train` path must differ from `val` path (unlike legacy).

---

*Folder structure v2 — training scope only.*
