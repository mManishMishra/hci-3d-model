# Annotation Plan — Prototype Training Batch 01

**Project:** IMPROVED_MODEL_1  
**Date:** 2026-06-10  
**Corpus:** `dataset_clean/images/` (314 JPG files)  
**Prototype batch:** `data/annotation_batch_01/` (50 images)  
**Manifest:** `data/annotation_batch_01/image_manifest.csv`

---

## 1. Executive Summary

All **314 cleaned images** are architectural floor plans suitable for BIM-oriented labeling. Automated inspection (OpenCV heuristics + visual sampling) confirms:

| Element | Corpus coverage (314 images) | Batch 01 (50 images) |
|---------|------------------------------|----------------------|
| **Walls** | 314 (100%) | 50 (100%) |
| **Doors** | 314 (100%) | 50 (100%) |
| **Windows** | 313 (99.7%) | 50 (100%) |
| **Rooms** (spatial regions) | 313 (99.7%) | 50 (100%) |
| **Furniture** (symbols/icons) | 80 (25.5%) | 15 furnished + partial symbols in line plans |

**Style breakdown (full corpus):**

| Style | Count | % | Annotation focus |
|-------|------:|--:|------------------|
| B&W line drawing | 271 | 86% | Walls, doors, windows, room polygons |
| Furnished color/render | 42 | 13% | Above + furniture/fixture boxes |
| Color rendered (minimal furnish) | 1 | <1% | Room + structural |

**Recommendation:** Use **instance segmentation** for structural elements and rooms; use **bounding boxes** for furniture and fixtures. Train in two phases: **Phase A (structural)** then **Phase B (interior objects)**.

---

## 2. Corpus Inspection Method

Each of the 314 images in `dataset_clean/images/` was analyzed programmatically:

| Signal | Method | Purpose |
|--------|--------|---------|
| Resolution | Image dimensions | Filter low-quality (<400px short edge) |
| Line density | Canny edge ratio | Confirm plan content / walls |
| Door arcs | Hough circle detection | Door symbol presence |
| Window cues | Line segment density | Window symbol presence |
| Style | HSV saturation | Line vs furnished color |
| Complexity | Hough line count | low / medium / high |
| Sharpness | Laplacian variance | Labeling clarity |

Visual spot-checks were performed on top-scored and furnished samples to validate heuristics.

**Note:** Room and furniture class tags in `image_manifest.csv` are **predicted visible classes** for prioritization, not ground truth. Annotators must confirm or correct during labeling.

---

## 3. Selection Criteria — Best 50 Images

Images were ranked by a composite **selection score** (resolution, sharpness, edge/line density, structural feature presence, style bonus) and then **stratified**:

| Stratum | Target | Selected |
|---------|--------|----------|
| B&W line drawings | 34 | 34 |
| Furnished color plans | 15 | 15 |
| Color rendered | 1 | 1 |
| **Total** | **50** | **50** |

**Inclusion rules:**
- Short edge ≥ 400 px (corpus minimum from cleaning pipeline)
- Prefer sharp, high-contrast B&W CAD plans for wall/door/window prototype
- Include furnished plans for furniture/fixture classes
- Exclude the one invalid image from the original clean run (not in corpus)

**Priority assignment (`annotation_priority`):**
- **P1** — High score, clear symbols, primary annotation queue (49 images)
- **P2** — Secondary queue (1 image)
- **P3** — Deferred / optional refinement

All 50 batch images are complex multi-room plans (high line density), which is appropriate for a BIM prototype but increases per-image effort.

---

## 4. Recommended Annotation Type

### 4.1 By class group

| Class group | Classes | Recommended format | Rationale |
|-------------|---------|-------------------|-----------|
| **Structural** | `wall`, `door`, `window` | **Instance segmentation (polygon)** | BIM pipeline needs precise boundaries; walls are irregular segments; doors/windows are small fixed symbols |
| **Spatial** | `bedroom`, `living_room`, `kitchen`, `bathroom`, `balcony` | **Semantic segmentation (room polygon)** | Rooms are enclosed regions; polygon → `IfcSpace` graph face |
| **Furniture** | `bed`, `wardrobe`, `sofa`, `table`, `chair` | **Bounding box** | Icon-style symbols; axis-aligned boxes sufficient for Phase 1 |
| **Fixtures** | `sink`, `toilet`, `stove` | **Bounding box** | Small sanitary/appliance symbols |

### 4.2 Why not all bounding boxes?

- **Walls** as boxes lose centerline geometry and thickness required for `BuildingGraph` → `WallData`.
- **Rooms** as boxes cannot represent L-shaped or non-rectangular spaces common in the corpus.
- YOLO-seg (project baseline) supports polygon labels natively.

### 4.3 Why not all segmentation?

- Furniture icons are axis-aligned and small; box annotation is **3–5× faster** with acceptable IoU for detection pre-training.
- Fixture symbols (toilet, sink) are standardized icons — boxes are sufficient for prototype.

### 4.4 Export format

| Stage | Format | Tool |
|-------|--------|------|
| Annotation | CVAT or Label Studio | Polygon + rectangle tools |
| Training export | **YOLO segmentation** (structural + rooms) | `labels/train/*.txt` |
| Training export | **YOLO detection** (furniture/fixtures) | Optional second head or separate model |
| BIM validation | `BuildingAnalysis` JSON | Graph builder adapter (future) |

---

## 5. Class Definitions

### 5.1 Structural classes

#### `wall`
**Definition:** Load-bearing or partition wall material shown as solid fill, double lines, or hatching between two parallel lines.

**Include:** Exterior walls, interior partitions, shaft walls.  
**Exclude:** Dimension lines, grid lines, furniture outlines, text labels.

**Annotation:** Polygon tracing the **visible wall footprint** (filled region). For double-line walls, trace the outer boundary of the wall strip.

**BIM mapping:** Centerline extraction (post-process) → `WallData`.

---

#### `door`
**Definition:** Door symbol consisting of a door leaf (line/rectangle) and swing arc, or sliding door tick marks.

**Include:** Entry doors, interior doors, sliding doors.  
**Exclude:** Window symbols, gaps without door symbol, cabinet doors.

**Annotation:** Tight polygon around leaf + swing arc (single instance per door).

**BIM mapping:** Opening center + width → `OpeningComponent` (`type=door`).

---

#### `window`
**Definition:** Window symbol — typically a break in the wall with parallel thin lines, or a glazed rectangle on exterior walls.

**Include:** Standard windows, bay window symbols.  
**Exclude:** Door symbols, mirror symbols, glass table tops.

**Annotation:** Polygon around window symbol including wall break.

**BIM mapping:** Opening center + width → `OpeningComponent` (`type=window`).

---

### 5.2 Room classes (semantic regions)

Room classes label **enclosed floor areas** bounded by walls. Only one room label per connected region.

#### `bedroom`
Sleeping room containing bed symbol or labeled "BEDROOM", "BR", "MBR", etc.

#### `living_room`
Living, drawing, lounge, family, or great room areas.

#### `kitchen`
Kitchen or kitchenette with counters, stove, or sink layout.

#### `bathroom`
Bathroom, toilet, WC, or combined bath/toilet wet areas (excluding open balcony).

#### `balcony`
Balcony, terrace, deck, porch, or veranda — typically exterior attached platform.

**Annotation:** Single polygon per room instance covering the walkable floor area **up to the inner wall face**.

**BIM mapping:** `RoomData.polygon` → future `IfcSpace`.

---

### 5.3 Furniture classes (bounding box)

#### `bed`
Mattress/bed symbol including pillows; single or double.

#### `wardrobe`
Wardrobe, closet, or WIR built-in shown as rectangular storage with door ticks.

#### `sofa`
Sofa, couch, or sectional seating symbol.

#### `table`
Dining table, coffee table, desk, or side table (not kitchen counter).

#### `chair`
Chair, armchair, or dining chair symbol.

---

### 5.4 Fixture / appliance classes (bounding box)

#### `sink`
Kitchen or bathroom sink basin (single or double).

#### `toilet`
WC / toilet bowl symbol.

#### `stove`
Cooktop, hob, range, or stove symbol (typically four burners).

---

## 6. Annotation Workflow

```
annotation_batch_01/*.jpg
        │
        ▼
   CVAT project (Batch 01)
        │
        ├── Layer 1: wall, door, window  (polygons)
        ├── Layer 2: room types          (polygons, 1 label per region)
        └── Layer 3: furniture/fixtures (boxes, furnished images only)
        │
        ▼
   Export → YOLO-seg labels
        │
        ▼
   dataset/labels/train/  (future ingest, not created yet)
```

### 6.1 Labeling order (per image)

1. **Walls** — largest regions first; snap to orthogonal where obvious  
2. **Rooms** — assign room type inside wall boundaries  
3. **Doors & windows** — instance polygons on wall openings  
4. **Furniture/fixtures** — boxes (furnished plans only)

### 6.2 Quality rules

- Polygon vertices: simplify to ≤20 points per wall segment where possible  
- No overlapping room polygons of different classes in the same pixel  
- Every door must touch a `wall` polygon edge  
- If room type is ambiguous, use best guess + `notes` field in CVAT (optional)

---

## 7. Batch 01 Manifest

**Location:** `data/annotation_batch_01/image_manifest.csv`

| Column | Description |
|--------|-------------|
| `filename` | JPG filename (copied from `dataset_clean/images/`) |
| `width` | Pixel width |
| `height` | Pixel height |
| `visible_classes` | Semicolon-separated predicted classes for annotator guidance |
| `annotation_priority` | `P1` / `P2` / `P3` |

**Batch composition:**

| Metric | Value |
|--------|------:|
| Images | 50 |
| P1 priority | 49 |
| P2 priority | 1 |
| Line drawing | 34 |
| Furnished color | 15 |
| Color rendered | 1 |
| Mean resolution | ~900 × 1350 px |

---

## 8. Annotation Effort Estimate

Estimates assume **one trained architectural annotator** using CVAT with polygon + box tools.

### 8.1 Per-image time (minutes)

| Task | Line drawing (34 img) | Furnished (15 img) | Notes |
|------|----------------------:|-------------------:|-------|
| Walls (polygon) | 18 | 20 | More clutter in furnished plans |
| Doors + windows | 8 | 10 | ~4–12 instances per plan |
| Room polygons (5 types) | 12 | 12 | 4–8 rooms per plan |
| Furniture/fixtures (box) | 0 | 18 | 15 images only |
| QA / review | 5 | 5 | Self-check pass |
| **Total per image** | **~43** | **~65** | |

### 8.2 Batch totals

| Scope | Images | Hours | Working days (8h) |
|-------|-------:|------:|----------------:|
| **Phase A — Structural only** (wall, door, window) | 50 | **~22 h** | ~3 days |
| **Phase B — Rooms** (+ room class polygons) | 50 | **+10 h** | ~1.5 days |
| **Phase C — Furniture/fixtures** (15 furnished) | 15 | **+5 h** | ~0.5 days |
| **Full Batch 01 (all classes)** | 50 | **~37 h** | **~5 days** |

### 8.3 Team scenarios

| Team | Calendar time (full batch) |
|------|---------------------------|
| 1 annotator | ~5 working days |
| 2 annotators (split 25/25) | ~3 working days |
| 1 annotator + 1 QA reviewer | ~6 working days (higher quality) |

### 8.4 Post-annotation overhead

| Activity | Estimate |
|----------|----------|
| CVAT export + format conversion | 2 h |
| Label validation script | 4 h (engineering, one-time) |
| Manual fix pass (10% labels) | 4 h |
| **Total overhead** | **~10 h** |

**Grand total (annotation + overhead):** **~47 hours** (~6 working days for one person).

---

## 9. Phased Training Recommendation

Do **not** train until Phase A labels are complete.

| Phase | Labels required | Model target |
|-------|-----------------|--------------|
| **Prototype 1** | wall, door, window | YOLOv8-seg nano |
| **Prototype 2** | + room classes | Multi-class seg |
| **Prototype 3** | + furniture/fixtures | Dual-head or second detector |

Minimum viable prototype: **50 images × structural classes** (~22 annotator-hours).

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Predicted `visible_classes` inaccurate | Annotator confusion | Treat manifest as hints; use class checklist in CVAT |
| Wall polygon inconsistency | Poor centerline extraction | Annotation guide with wall tracing examples |
| Room label ambiguity | Noisy room classifier | Allow `living_room` as default for open plans |
| All 50 images high complexity | Long annotation time | Start with 10-image pilot; refine guide |
| Furnished vs line style mismatch | Domain gap | Stratified training; weighted sampling |
| No OCR ground truth for room names | Wrong room type | OCR assist in Phase 2, not blocking prototype |

---

## 11. Next Steps

1. Create CVAT project **IMPROVED_MODEL_01_Batch01** with class list from Section 5  
2. Import 50 images from `data/annotation_batch_01/`  
3. Run **10-image pilot** (~8 h) and refine wall-tracing guide  
4. Complete Phase A structural labels (50 images)  
5. Export to YOLO-seg → `dataset/labels/train/` (future task)  
6. Begin training only after label QA passes  

---

## 12. Related Documents

| Document | Path |
|----------|------|
| Clean dataset report | `docs/CLEAN_DATASET_REPORT.md` |
| Full corpus audit | `docs/DATASET_AUDIT.md` |
| System design | `docs/HLD.md`, `docs/LLD.md` |
| Full analysis CSV | `data/analysis_all_images.csv` |
| Selection stats | `data/batch_selection_stats.json` |

---

*No training performed. `dataset_clean/` was not modified — batch images are copies only.*
