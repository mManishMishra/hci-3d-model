# CANONICAL ANNOTATION RULEBOOK

**Project:** IMPROVED_MODEL_1  
**Version:** 2.0 — 7-CLASS LOCKED  
**Date:** 2026-06-19  
**Scope:** YOLO11 instance **segmentation** — 7-class floor-plan training

**Primary goal:** YOLO11-seg model (classes 0–6) that outperforms `web_file` / `web2`.

**Active config:** `data/prototype_7_classes.yaml`

---

## 1. Active Class List (LOCKED)

| YOLO ID | Name | Shape | Annotate every image? |
|--------:|------|-------|----------------------|
| **0** | `wall` | Closed polygon | **YES** |
| **1** | `door` | Closed polygon | **YES** (if visible) |
| **2** | `window` | Closed polygon | **YES** (if visible) |
| **3** | `bedroom` | Closed polygon | **YES** (if identifiable) |
| **4** | `living_room` | Closed polygon | **YES** (if identifiable) |
| **5** | `kitchen` | Closed polygon | **YES** (if identifiable) |
| **6** | `bathroom` | Closed polygon | **YES** (if identifiable) |

**Do not use** 3-class-only or 11-class training configs. Symbol bbox classes are **deferred**.

**Legacy:** `web_file` `Room` perimeter loops are **not** walls — never substitute.

---

## 2. General Rules

### DO

- CVAT project: `IMPROVED_MODEL_1_7Class_Seg`
- Polygon tool for **all** seven classes
- Annotate order: **wall → door → window → bedroom → living_room → kitchen → bathroom**
- One polygon per instance; minimum 4 vertices
- Zoom 200–400% for doors/windows
- Save every 2 images

### DO NOT

- Annotate text, dimensions, furniture, fixtures as geometry classes
- Use room perimeter as `wall`
- Span openings with `wall` polygons
- Use bounding boxes (seg only for all 7 classes)

---

## 3. Structural classes (0–2)

### Wall (0)

- Full **visible wall thickness** footprint
- **Split at every corner/junction**
- **Stop at openings** — leave gap for door/window
- 15–40 instances typical

### Door (1)

- Leaf + swing arc in opening gap only
- No adjacent wall mass

### Window (2)

- Window symbol in opening gap only

---

## 4. Room classes (3–6)

### Definition

**Interior floor boundary** of each named space — the walkable/usable floor area **inside** walls.

### Polygon rule

1. Trace the **inner edge** of surrounding walls (inside face)
2. Exclude wall thickness, doors (opening gaps), windows, furniture, fixtures
3. One polygon per room **instance** per class label
4. If room type is ambiguous, use best-effort label + note in CVAT issue tracker
5. Open-plan areas: split by visible partition walls; if single undivided space, use dominant room type

### DO NOT

- Trace outer building perimeter as a single room
- Include wall hatch/fill in room polygon
- Duplicate wall geometry as room
- Label corridors/closets unless clearly bedroom/kitchen/bath/living

### Typical count

2–8 room polygons per residential plan

---

## 5. CVAT setup

| Label | Color |
|-------|-------|
| wall | `#FF0000` |
| door | `#00CC00` |
| window | `#0066FF` |
| bedroom | `#FFE066` |
| living_room | `#66CCFF` |
| kitchen | `#FF9999` |
| bathroom | `#66CCCC` |

---

## 6. Export rules

- Format: **YOLO 1.1 segmentation**
- Class IDs must be **0–6** (verify after export)
- Layout:

```
data/prototype_7_batch/
├── images/train/   images/val/
└── labels/train/   labels/val/
```

- Split: manifest ranks **1–20 train**, **21–25 val**
- Import: `python scripts/export_cvat_to_yolo.py <cvat_export> --validate`

### Post-export validation

```bash
python scripts/validate_labels.py
python scripts/check_dataset_integrity.py
```

---

## 7. Training reference

| Parameter | Value |
|-----------|-------|
| model | `yolo11n-seg.pt` |
| imgsz | 1024 |
| epochs | 50 |
| batch | 4 |
| dataset | `data/prototype_7_batch/dataset.yaml` |
| nc | 7 |

---

## 8. Quick reference

```
STRUCTURAL: full-thickness walls, split at corners, gap at openings
ROOMS:      interior floor boundary inside walls — NOT wall perimeter loops
ORDER:      wall → door → window → rooms
IDS:        0–6 only
EXPORT:     YOLO 1.1 seg → validate → train
```

---

*Authoritative 7-class annotation specification for IMPROVED_MODEL_1.*
