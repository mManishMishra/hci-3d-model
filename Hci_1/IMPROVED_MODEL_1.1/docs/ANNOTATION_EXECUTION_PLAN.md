# Annotation Execution Plan — 7-Class Batch

**Batch:** `data/prototype_7_batch/` (25 images)  
**Config:** `data/prototype_7_classes.yaml`  
**CVAT project:** `IMPROVED_MODEL_1_7Class_Seg`

---

## Classes (0–6)

wall, door, window, bedroom, living_room, kitchen, bathroom — **all polygons**

---

## Steps

### 1. CVAT setup (30 min)

- Create project with 7 polygon labels (colors in rulebook)
- Import images from `data/prototype_7_batch/images/` (flat) or train+val folders

### 2. Annotation (20–30 hours)

- Follow [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md)
- Order: wall → door → window → rooms
- Val set (ranks 21–25): 100% peer review

### 3. Export (1 hour)

- CVAT → YOLO 1.1 segmentation export

### 4. Import + validate

```bash
python scripts/export_cvat_to_yolo.py path/to/cvat/export --validate
python scripts/check_dataset_integrity.py
```

### 5. Train (after labels pass)

```bash
python scripts/train.py --data data/prototype_7_batch/dataset.yaml
python scripts/evaluate.py --weights runs/prototype_7_seg/weights/best.pt
```

---

## Split

| Split | Manifest ranks | Count |
|-------|----------------|------:|
| train | 1–20 | 20 |
| val | 21–25 | 5 |

Refresh folders:

```bash
python scripts/split_batch_from_manifest.py --write-dataset-yaml
```

---

## Current status

| Item | Status |
|------|--------|
| Images split train/val | ✅ |
| dataset.yaml | ✅ |
| Labels exported | ⏳ Pending CVAT |

---

*7-class execution plan — replaces 3-class and 11-class plans.*
