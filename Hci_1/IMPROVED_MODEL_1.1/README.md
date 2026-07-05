# IMPROVED_MODEL_1

**YOLO11 7-class floor-plan instance segmentation training system**

Outperforms legacy `web_file` / `web2` through high-quality CVAT annotation, strict YOLO export validation, and reproducible Ultralytics training.

---

## Current phase

**ANNOTATION → DATASET BUILD → FIRST TRAINING RUN**

| Step | Status |
|------|--------|
| Dataset batch staged (`prototype_7_batch`) | ✅ 25 images, 20 train / 5 val |
| CVAT annotation (7 classes) | 🔄 In progress |
| Label export + validation | ⏳ After CVAT |
| YOLO11 training | ⏳ After labels |
| Evaluation vs legacy | ⏳ After training |

---

## Locked 7-class taxonomy

| ID | Class | Annotation |
|----|-------|------------|
| 0 | `wall` | Polygon — full wall thickness |
| 1 | `door` | Polygon — opening symbol |
| 2 | `window` | Polygon — opening symbol |
| 3 | `bedroom` | Polygon — interior floor boundary |
| 4 | `living_room` | Polygon — interior floor boundary |
| 5 | `kitchen` | Polygon — interior floor boundary |
| 6 | `bathroom` | Polygon — interior floor boundary |

**Active config:** `data/prototype_7_classes.yaml`  
**Do not use** 3-class or 11-class yaml files for training.

---

## Pipeline

```
CVAT (7 labels)
    → export YOLO 1.1 seg
    → scripts/export_cvat_to_yolo.py
    → scripts/validate_labels.py
    → scripts/check_dataset_integrity.py
    → scripts/train.py (YOLO11n-seg)
    → scripts/evaluate.py
```

---

## Dataset layout

```
data/prototype_7_batch/
├── images/train/     # 20 images (manifest ranks 1–20)
├── images/val/       # 5 images (ranks 21–25)
├── labels/train/     # one .txt per image (after export)
├── labels/val/
├── manifest.csv
└── dataset.yaml
```

Regenerate splits:

```bash
python scripts/split_batch_from_manifest.py --write-dataset-yaml
```

---

## Quick start (annotators)

1. Read `docs/CANONICAL_ANNOTATION_RULEBOOK.md`
2. CVAT project: `IMPROVED_MODEL_1_7Class_Seg`
3. Annotate order: **wall → door → window → rooms**
4. Export YOLO 1.1 segmentation
5. Import:

```bash
python scripts/export_cvat_to_yolo.py path/to/cvat/export --validate
```

---

## Quick start (training)

```bash
pip install -r requirements.txt
python scripts/validate_labels.py
python scripts/check_dataset_integrity.py
python scripts/train.py --data data/prototype_7_batch/dataset.yaml
python scripts/evaluate.py --weights runs/prototype_7_seg/weights/best.pt
```

Training is blocked until label files exist in `labels/train` and `labels/val`.

---

## Project structure (active)

```
IMPROVED_MODEL_1/
├── data/prototype_7_batch/    # Active YOLO dataset
├── data/prototype_7_classes.yaml
├── scripts/
│   ├── split_batch_from_manifest.py
│   ├── export_cvat_to_yolo.py
│   ├── validate_labels.py
│   ├── check_dataset_integrity.py
│   ├── train.py
│   └── evaluate.py
├── src/
│   ├── preprocessing/         # Image normalize (optional)
│   ├── dataset_tools/         # Cleaner + YOLO label utils
│   └── _deferred/             # Out-of-scope stubs (not imported)
└── docs/                      # Annotation + design docs
```

---

## Legacy comparison

| | `web_file` / `web2` | IMPROVED_MODEL_1 |
|---|---------------------|------------------|
| Labels | Mock auto-label (empty) | CVAT human polygons |
| Classes | 17 (Room loops) | **7** structural + spaces |
| Model | YOLOv8-seg | **YOLO11n-seg** |
| Val split | train=val=test | **20/5 proper split** |
| Training | Web UI only | **CLI `scripts/train.py`** |

---

## Deferred (not in active pipeline)

Modules under `src/_deferred/` (graph, topology, BIM schema, IFC, full pipeline) and 37-class analysis scripts under `scripts/_deferred/` are preserved but **not used** for training.

---

## Documentation

See `docs/README.md` for the full document index.
