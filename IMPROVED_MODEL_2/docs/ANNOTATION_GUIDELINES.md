# Annotation Guidelines

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19  
**Authority:** Superseded by specifics in [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) — this document is the annotator-facing summary.

---

## System Goal

Produce human-verified YOLO segmentation labels for **wall, door, window** that enable a YOLO11 model to outperform legacy `web_file` / `web2`.

---

## Active Classes (Training Only)

| YOLO ID | Name | Tool | Color |
|--------:|------|------|-------|
| 0 | `wall` | Polygon | Red `#FF0000` |
| 1 | `door` | Polygon | Green `#00CC00` |
| 2 | `window` | Polygon | Blue `#0066FF` |

**Only these three classes.** Do not annotate rooms, furniture, fixtures, or symbols for the current milestone.

---

## CVAT Project Setup

| Setting | Value |
|---------|-------|
| Project name | `IMPROVED_MODEL_1_Structural_Seg` |
| Task type | Instance segmentation (polygons) |
| Export format | YOLO 1.1 segmentation |

---

## General Annotation Rules

### DO

1. Annotate in order: **wall → door → window**
2. One polygon per object instance
3. Minimum 4 vertices per polygon
4. Zoom to 200–400% for doors and windows
5. Use Shift for orthogonal wall snaps
6. Save after every 2 images
7. Trace only visible ink on the plan

### DO NOT

1. Annotate text, dimensions, north arrows, title blocks, grid lines
2. Annotate furniture or appliances
3. Use room perimeter loops as walls (legacy `web_file` mistake)
4. Use wall centerlines — trace **full wall thickness**
5. Merge wall segments at corners into one polygon
6. Span door/window openings with wall polygons
7. Use bounding boxes for structural classes

---

## Class-Specific Rules

### Wall (class 0)

- Trace the **full visible wall footprint** (hatched fill or double-line mass)
- **Split at every corner and junction**
- **Stop at openings** — leave gap for door/window polygons
- Typical: 15–40 polygons per plan

### Door (class 1)

- Polygon around door leaf + swing arc (if drawn)
- Sits in wall opening gap only — no wall mass included
- Typical: 4–15 per plan

### Window (class 2)

- Polygon around window symbol only
- Sits in wall opening gap only
- Typical: 3–20 per plan

---

## Export & Validation

1. Export YOLO 1.1 segmentation from CVAT
2. **Verify class IDs:** wall=0, door=1, window=2 (remap if CVAT reorders)
3. Place files in `data/prototype_11_batch/labels/{train,val}/`
4. Run validation before training (see rulebook §7)
5. Val set (ranks 21–25) requires 100% secondary review

---

## Train/Val Split

| Split | Manifest ranks | Count |
|-------|----------------|------:|
| train | 1–20 | 20 |
| val | 21–25 | 5 |

Source: `data/prototype_11_batch/manifest.csv`

---

## Deferred (Do Not Annotate Now)

- Bedroom, living room, kitchen, bathroom polygons
- Bed, WC, sink, stove bounding boxes
- Any class from `prototype_11_classes.yaml` IDs 3–10
- Full 37-class taxonomy from `CLASS_TAXONOMY.md`

These are future phases — only after structural mAP beats legacy.

---

## Draft Annotator Helper

`scripts/cursor_draft_annotator.py` produces heuristic drafts for human correction in CVAT. **Never use as ground truth without full review.**

---

*Guidelines v2 — aligned to CANONICAL_ANNOTATION_RULEBOOK.md*
