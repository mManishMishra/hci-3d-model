# Dataset Audit Report

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Location:** `D:\HCI_interor\IMPROVED_MODEL_1\data`  
**Version:** 2.0  
**Last updated:** 2026-06-19

---

## System Goal

Assess dataset readiness for YOLO11 **wall, door, window** segmentation training vs legacy `web_file` / `web2`.

---

## Executive Summary

| Finding | Status (2026-06-19) |
|---------|---------------------|
| Raw floor plan images | ✅ Available (~315 unique after dedup) |
| Active annotation batch | ✅ 25 images in `prototype_11_batch/` |
| Pilot batch | ✅ 13 images in `prototype_dataset/` |
| Phase 2 pool | ✅ 50 images in `annotation_batch_01/` |
| **YOLO segmentation labels** | ❌ **0 files** |
| Train/val split (labels) | ❌ Not created |
| `dataset.yaml` for active batch | ❌ Not created |
| Training runs | ❌ None |

**Bottom line:** Images exist. **Labels do not.** Training is blocked until CVAT export completes.

---

## Active Batches

| Batch | Path | Images | Classes | Split |
|-------|------|-------:|---------|-------|
| **Primary** | `prototype_11_batch/` | 25 | 0–2 only | 20 train / 5 val (manifest) |
| Pilot | `prototype_dataset/` | 13 | 0–2 | 8 train / 2 val (original plan) |
| Phase 2 | `annotation_batch_01/` | 50 | 0–2 | TBD after Phase 1 |

---

## Image Corpus (Full `data/`)

| Metric | Value |
|--------|-------|
| Total files scanned | ~570 |
| Unique raster images | ~315 (after MD5 dedup) |
| Duplicate `Era/` subfolder | 140 images — **exclude from training** |
| PDFs (furniture layouts) | 34 — not used for seg training |
| Annotations | **0** YOLO `.txt` files |

### Resolution notes

- Majority below 1 megapixel — use `imgsz=1024` for training
- Letterbox resize safe for YOLO
- Very tall plans (up to ~2000px) — handled by Ultralytics letterbox

---

## Required Directory Layout (Post-Export)

```
data/prototype_11_batch/
├── images/
│   ├── train/          # ranks 1–20
│   └── val/            # ranks 21–25
├── labels/
│   ├── train/          # one .txt per image
│   └── val/
├── manifest.csv
└── dataset.yaml        # nc: 3
```

---

## Dataset Quality Rules

1. **Deduplicate** on content hash before training (`dataset_cleaner.py`)
2. **Exclude** `data/Era/` — exact duplicates of root files
3. **Never** use train=val=test (legacy `web_file` flaw)
4. **Pair** every image with exactly one label file
5. **Validate** all class_id ∈ {0, 1, 2} before train

---

## Readiness Checklist

| Requirement | Status |
|-------------|--------|
| Images for annotation | ✅ |
| Annotation rulebook | ✅ `CANONICAL_ANNOTATION_RULEBOOK.md` |
| CVAT project defined | ✅ `IMPROVED_MODEL_1_Structural_Seg` |
| Labels exported | ❌ |
| Label validation script | ❌ Planned |
| Training script | ❌ Planned |
| Baseline comparison setup | ❌ Planned |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Zero labels | Critical | Annotation sprint — classes 0–2 only |
| Small train set (20) | High | Heavy augmentation; expand to 50 after baseline |
| Era/ duplication | Medium | Exclude on ingest |
| No valid metrics yet | High | Proper val split + evaluate vs legacy |

---

## Recommended Sequence

1. Annotate `prototype_11_batch/` (classes 0–2)
2. Export → `labels/{train,val}/`
3. Create `dataset.yaml` (`nc: 3`)
4. Validate labels
5. Train YOLO11n-seg
6. Evaluate vs `web_file` on same val set
7. Expand to `annotation_batch_01/` (50 more images)

---

## Deferred

- Full 37-class taxonomy training
- 11-class mixed seg+det labels
- Pseudo-label bootstrap from SVG (not in current milestone)
- Using unlabeled corpus for unsupervised pre-training

---

*Dataset audit v2 — YOLO11 segmentation training scope. Original scan data from 2026-06-10 audit preserved in git history.*
