# Annotation Guidelines — IMPROVED_MODEL_1

**Version:** 1.1  
**Date:** 2026-06-11  
**Taxonomy:** 37 BIM classes (`data/classes.yaml`)  
**Prototype taxonomy:** 11 classes (`data/prototype_11_classes.yaml`)  
**Tool:** CVAT (recommended) or Roboflow  
**Export format:** YOLO 1.1 seg (polygons) + YOLO detect (bounding boxes)  
**Companion docs:** `docs/CLASS_TAXONOMY.md` · `docs/PROTOTYPE_11_CLASS_PLAN.md`

---

## 1. Overview

### What to annotate

The **active prototype** uses **11 classes** with mixed annotation types:

| Type | Classes | Shape |
|------|---------|-------|
| **Polygon** | wall, door, window, bedroom, living_room, kitchen, bathroom | Closed polygon (YOLO seg) |
| **Bounding box** | bed, wc, sink, stove | Axis-aligned rectangle (YOLO detect) |

Each visible instance gets one shape and one prototype class ID (0–10).

### Training phases

| Phase | Classes | When |
|-------|---------|------|
| **Prototype (active)** | 11 classes — see `data/prototype_11_classes.yaml` | Current annotation target |
| **Production Phase 2+** | Remaining 26 classes from 37-class schema | After prototype validates |

**Rule:** Do not annotate classes outside the active prototype scope unless a batch is explicitly expanded.

### Quality targets

| Metric | Target |
|--------|--------|
| Polygon vertex density | Follow curvature; no more than ~2 px spacing on straight walls |
| Wall gap at corners | ≤ 2 px after snap |
| Door swing arc | Include full swing polygon if drawn |
| Class confusion | Zero tolerance between door vs window, wc vs bathroom |
| Review pass | 100% of val set reviewed by second annotator |

---

## 2. General rules

### 2.1 Polygon drawing (structural + rooms)

1. Trace the **visible ink** of the symbol or wall centerline band.
2. Close every polygon; no open polylines.
3. One instance = one polygon. Double doors = one polygon if drawn as one opening.
4. Overlapping objects: draw both polygons; z-order does not matter for YOLO.
5. Partially cropped instances at image edge: annotate visible portion only.

### 2.1b Bounding box drawing (bed, wc, sink, stove)

1. Draw the **smallest axis-aligned rectangle** fully containing the symbol.
2. Include the full icon footprint — mattress outline for bed, bowl for wc, basin bowl for sink, cooktop for stove.
3. Do **not** annotate symbol classes on line-drawing plans where symbols are absent.
4. One instance = one box. Overlapping symbols get separate boxes.
5. Tight boxes preferred; ≤ 3 px padding on each side at export resolution.

### 2.2 What NOT to annotate

- Dimension text, north arrows, scale bars, title blocks
- Hatching fills that are not room labels
- Symbol bboxes (bed, wc, sink, stove) on plans where symbols are not drawn
- Speculative objects not drawn on the plan
- Scan noise, crease marks, punch-hole artifacts

### 2.3 File naming

- Label file must match image stem: `plan_uuid.jpg` → `plan_uuid.txt`
- Place under `labels/train/` or `labels/val/` mirroring `images/`

### 2.4 CVAT setup

1. Create project: **IMPROVED_MODEL_1_Prototype_11**
2. Import label map from `data/prototype_11_classes.yaml`
3. Enable **polygons** for classes 0–6 and **rectangles** for classes 7–10
4. Export polygons → **YOLO 1.1 seg**; export boxes → **YOLO detect**

---

## 3. Class-by-class guidelines

### Prototype 11 — Structural (polygon, all images)

#### 0 — `wall` (red `#FF0000`)

**Annotate:** All load-bearing and partition wall segments visible as lines or filled bands.

| Do | Don't |
|----|-------|
| Trace wall centerline thickness (typical 2–6 px band on B&W plans) | Include door/window openings inside wall polygon |
| Include exterior and interior walls | Trace dimension lines |
| Merge collinear segments if drawn as one wall | Split one wall into multiple IDs unless physically distinct |

**BIM note:** Centerline will be extracted in graph builder; polygon is for detection training.

---

#### 1 — `door` (green `#00CC00`)

**Annotate:** Door symbols including leaf, frame, and swing arc if present.

| Do | Don't |
|----|-------|
| Include swing quarter-circle | Label windows with glazing lines as doors |
| One polygon per door opening | Include entire wall segment |
| Annotate sliding doors as rectangular opening symbol | |

**Variants:** Hinged, sliding, bi-fold — all use class `door`.

---

#### 2 — `window` (blue `#0066FF`)

**Annotate:** Window symbols — typically parallel lines or thin rectangles in walls.

| Do | Don't |
|----|-------|
| Trace full window symbol width | Confuse French doors (use door if swing shown) |
| Include bay window footprint as one polygon | |

---

#### 3 — `column` (purple `#9933FF`) — Train Later

**Annotate:** Structural column squares/circles (filled or outline).

---

#### 4 — `stair` (orange `#FF6600`) — Train Later

**Annotate:** Full stair footprint including tread outlines and direction arrow area.

---

### Prototype 11 — Rooms (polygon, all images)

Room classes label **space boundaries**, not furniture inside.

#### 3 — `bedroom` | 4 — `living_room` | 5 — `kitchen` | 6 — `bathroom`

*Production taxonomy IDs: 5, 7, 9, 10.*

**Annotate:** Closed polygon following interior wall faces bounding the labeled space.

| Do | Don't |
|----|-------|
| Follow inner face of walls | Include furniture |
| Use label text on plan as hint (e.g. "BEDROOM") | Overlap into adjacent room |
| Split open-plan only when plan shows distinct labels | |

### Prototype 11 — Symbols (bounding box, furnished images only)

Annotate **only when the symbol is visible** on furnished or color-rendered plans.

#### 7 — `bed` (brown `#8B4513`) — bounding box

| Do | Don't |
|----|-------|
| Box the mattress / bed outline symbol | Polygon-annotate bed |
| Annotate when "BED" label or bed icon is drawn | Guess bed location in empty bedroom |
| One box per bed instance | Include nightstands in bed box |

*Production taxonomy ID: 15.*

#### 8 — `wc` (grey `#E0E0E0`) — bounding box

| Do | Don't |
|----|-------|
| Box the toilet bowl fixture symbol | Confuse with bathroom room polygon (id 6) |
| Annotate inside bathroom space | Label entire bathroom as wc |

*Production taxonomy ID: 27.*

#### 9 — `sink` (teal `#5F9EA0`) — bounding box

| Do | Don't |
|----|-------|
| Box kitchen or bathroom sink symbol | Include full counter as sink |
| Separate kitchen sink from bathroom basin when both shown | Merge two sinks into one box |

*Production taxonomy ID: 31.*

#### 10 — `stove` (orange `#FF4500`) — bounding box

| Do | Don't |
|----|-------|
| Box cooktop / range symbol | Include entire kitchen room |
| Include burner circles inside box | Label refrigerator as stove |

*Production taxonomy ID: 32.*

---

### Production-only classes (not in prototype 11)

#### `master_bedroom` — deferred

Use when plan explicitly labels "Master Bedroom" / "MBR". Otherwise use `bedroom`.

#### `dining_room` | `toilet` room | `balcony` | `utility` | `corridor` — deferred

Annotate when the plan explicitly shows the space label or unambiguous boundary.

---

### Furniture — production (deferred)

Annotate only on **furnished** or **color-rendered** plans.

| ID | Class | Drawing cues |
|----|-------|--------------|
| 15 | bed | *(in prototype 11 as bbox id 7)* |
| 16 | wardrobe | Wall-aligned cabinet with door swings |
| 17 | sofa | Upholstered seating, often L-shape |
| 18 | chair | Single seat symbol |
| 19 | dining_table | Table with 4+ chairs nearby |
| 20 | coffee_table | Small table in living area |
| 21 | study_table | Desk with chair |
| 22 | tv_unit | Low console on wall |
| 23 | side_table | Small table beside sofa/bed |
| 24 | dresser | Chest of drawers |
| 25 | storage_unit | Generic storage (non-kitchen) |
| 26 | cabinet | Kitchen base/upper units (not appliances) |

**`table` disambiguation:** Use `dining_table` when ≥3 chairs adjacent; `coffee_table` in living room; `study_table` with desk chair; `side_table` otherwise.

---

### Fixtures — Train Later

| ID | Class | Drawing cues |
|----|-------|--------------|
| 27 | wc | Toilet bowl symbol (annotate on furnished plans) |
| 28 | wash_basin | Bathroom basin oval/rectangle |
| 29 | shower | Shower tray or shower head + tray |
| 30 | bathtub | Elongated tub outline |
| 31 | sink | Kitchen or utility sink symbol |

**`wc` vs `toilet` room:** `wc` = fixture symbol inside bathroom; `toilet` (id 11) = separate WC room space.

---

### Appliances — Train Later

| ID | Class | Drawing cues |
|----|-------|--------------|
| 32 | stove | Cooktop / range rectangles with burners |
| 33 | refrigerator | Tall rectangle with door line |
| 34 | washing_machine | Circle-in-square or labeled WM |
| 35 | microwave | Small rectangle on counter |
| 36 | chimney | Hood above stove |

---

## 4. Prototype workflow (11 classes)

Config: `data/prototype_11_classes.yaml`  
Plan: `docs/PROTOTYPE_11_CLASS_PLAN.md`

### Step-by-step

1. Select batch (10 / 25 / 50) from `dataset_clean/images/` into a **new** folder (do not modify `dataset_clean/`)
2. Tag images: `line_drawing` vs `furnished`
3. **All images:** polygon-annotate classes 0–6 (wall → bathroom)
4. **Furnished only:** bbox-annotate classes 7–10 where symbols exist
5. Export seg labels → `labels/seg/{train,val}/`
6. Export det labels → `labels/det/{train,val}/`

### Validation

```powershell
# Segmentation labels required on every image
Get-ChildItem data/prototype_dataset/images/train/*.jpg | ForEach-Object {
  $label = "data/prototype_dataset/labels/seg/train/$($_.BaseName).txt"
  if (-not (Test-Path $label)) { Write-Host "MISSING SEG: $label" }
}
```

See also: `docs/PROTOTYPE_ANNOTATION_GUIDE.md` (legacy 3-class sprint notes)

---

## 5. YOLO export validation

**Segmentation** (`labels/seg/`) — polygon classes 0–6:

```
<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>
```

**Detection** (`labels/det/`) — bbox classes 7–10:

```
<class_id> <x_center> <y_center> <width> <height>
```

Checks before training:

- [ ] Prototype `class_id` in range `0..10`
- [ ] Seg IDs only 0–6; det IDs only 7–10
- [ ] All coordinates in `[0, 1]`
- [ ] Minimum 3 vertices per polygon
- [ ] Bbox width/height > 0
- [ ] Train/val image stems match label stems

---

## 6. Class ID quick reference (prototype 11)

| Proto ID | Class | Annotation | Color |
|---------:|-------|--------------|-------|
| 0 | wall | polygon | `#FF0000` |
| 1 | door | polygon | `#00CC00` |
| 2 | window | polygon | `#0066FF` |
| 3 | bedroom | polygon | `#FFE066` |
| 4 | living_room | polygon | `#66CCFF` |
| 5 | kitchen | polygon | `#FF9999` |
| 6 | bathroom | polygon | `#66CCCC` |
| 7 | bed | bounding box | `#8B4513` |
| 8 | wc | bounding box | `#E0E0E0` |
| 9 | sink | bounding box | `#5F9EA0` |
| 10 | stove | bounding box | `#FF4500` |

Full 37-class production table: `docs/CLASS_TAXONOMY.md` §5.

---

## 7. Review checklist

Before marking a batch complete:

- [ ] All images in batch annotated
- [ ] Val set independently reviewed
- [ ] No text/dimension annotations included
- [ ] Door/window confusion spot-checked (≥10 samples)
- [ ] wc vs bathroom room confusion spot-checked
- [ ] Symbol bboxes only on furnished images where symbols exist
- [ ] Export opens in YOLO without parse errors
- [ ] `prototype_11_classes.yaml` `nc: 11` matches exported class count
- [ ] Label count per class logged for imbalance review

---

## 8. Related files

| File | Purpose |
|------|---------|
| `data/classes.yaml` | Master taxonomy, IDs, colors |
| `data/prototype_11_classes.yaml` | **Active** 11-class prototype config |
| `data/prototype_classes.yaml` | Legacy 3-class config (superseded) |
| `docs/PROTOTYPE_11_CLASS_PLAN.md` | Prototype training plan |
| `data/class_support_analysis.json` | Visual class support analysis |
| `scripts/analyze_class_taxonomy.py` | Regenerate frequencies |
