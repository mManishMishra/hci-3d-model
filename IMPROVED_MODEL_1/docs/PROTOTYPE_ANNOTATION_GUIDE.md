# Prototype Annotation Guide — 10-Hour Pipeline

**Goal:** `Image → Detection (wall/door/window) → Building JSON → IFC`  
**Scope:** 3 classes only. No rooms. No furniture.  
**Dataset:** 10 images in `data/prototype_dataset/`  
**Classes:** `data/prototype_classes.yaml`

---

## 1. Ten-Hour Schedule

| Hour | Task | Output |
|------|------|--------|
| **0–0.5** | CVAT setup + import 10 images | Project ready |
| **0.5–3.5** | Manual annotation (10 images) | CVAT polygons |
| **3.5–4** | Export YOLO 1.1 seg + copy labels | `labels/train`, `labels/val` |
| **4–5** | Train YOLO11n-seg (50 epochs) | `runs/prototype/weights/best.pt` |
| **5–6** | Inference + overlay QA on val set | Detection JSON |
| **6–8** | Wire graph builder stub → BuildingAnalysis JSON | `building.json` |
| **8–9** | IFC via V3 adapter | `model.ifc` |
| **9–10** | Viewer check + document blockers | Demo complete |

**Annotation budget:** ~3 hours for 10 images (~18 min/image average).

---

## 2. Selected 10 Images

Curated from `data/annotation_batch_01/` for **fast B&W structural labeling**.

| # | Filename | Split | Size | Why selected |
|---|----------|-------|------|--------------|
| 1 | `22177c44-e3e1-4d32-8f5f-449416c7f28f.jpg` | **val** | 964×1600 | Simplest — 3 rooms, crisp symbols |
| 2 | `ae4cdbb8-e2b5-4e03-82e5-26c97c0abeb6.jpg` | train | 1200×1170 | Clean structural, no furniture |
| 3 | `852f2a15-23c8-45aa-93f4-e65267a48d12.jpg` | **val** | 1024×882 | Compact landscape plan |
| 4 | `577f8173-8c69-4ac6-a63c-d9ffdcbc3e43.jpg` | train | 736×1234 | Medium complexity |
| 5 | `ebb42e5a-9488-49bd-9b26-ffa78743e87f.jpg` | train | 821×1280 | Standard B&W CAD |
| 6 | `938c6fc1-381d-4e9b-83d7-0d5e1aa709e2.jpg` | train | 1200×1095 | Square plan |
| 7 | `72aab0a0-c546-4e47-addd-abd510c5bf79.jpg` | train | 1200×927 | Landscape |
| 8 | `4a17677b-cff0-4922-a564-4768195fe5a9.jpg` | train | 1200×899 | Landscape |
| 9 | `ef320344-ea55-4976-9b95-0f1e1dc643ad.jpg` | train | 1200×1200 | Square multi-room |
| 10 | `009b1b7a-ff37-4d1a-9d6c-47b8bd4862b2.jpg` | train | 775×1280 | Metric CAD — 1 complex example |

**Split:** 8 train / 2 val  
**Manifest:** `data/prototype_dataset/prototype_manifest.csv`

**Annotate in this order** (easiest first):
1. `22177c44...` → 2. `852f2a15...` → 3. `ae4cdbb8...` → … → 10. `009b1b7a...`

---

## 3. Classes (3 only)

| ID | Name | Color (CVAT) | Annotation type |
|----|------|--------------|-----------------|
| 0 | `wall` | Red `#FF0000` | Polygon |
| 1 | `door` | Green `#00CC00` | Polygon |
| 2 | `window` | Blue `#0066FF` | Polygon |

Reference: `data/prototype_classes.yaml`

---

## 4. Exact Annotation Instructions

### 4.1 General rules

1. **Zoom to 200–400%** when tracing doors/windows.
2. **Do not label** text, dimensions, north arrows, title blocks, furniture, fixtures, or grid lines.
3. **One polygon per instance** — each wall segment, each door, each window is separate.
4. **Minimum 4 vertices** per polygon (3 is invalid for YOLO-seg).
5. Use **orthogonal snaps** where walls are straight (hold Shift in CVAT).
6. **Save every 2 images** (Ctrl+S habit).

### 4.2 `wall` — polygon

**What to trace:** The filled wall footprint (the thick black hatched or double-line region).

**How:**
1. Click along the **outer boundary** of the wall strip.
2. For double-line walls, trace the **outer edge** of the wall mass (not the centerline).
3. Split long walls into **segments between corners** (one polygon per straight wall run).
4. Include exterior and interior walls.
5. **Stop** at door/window openings — do not cover the opening gap.

**Do NOT include:**
- Dimension lines
- Furniture outlines inside rooms
- Stair tread lines (outline the stairwell wall only)

**Typical count per image:** 15–40 wall polygons.

### 4.3 `door` — polygon

**What to trace:** Door leaf line **plus** swing arc as one tight bounding polygon.

**How:**
1. Draw a polygon that encloses:
   - The straight door leaf (thin line)
   - The quarter-circle swing arc
2. For sliding doors (parallel lines, no arc): polygon around the door opening gap in the wall.
3. Each door = **one polygon**, class `door`.

**Do NOT include:** The wall on either side (wall is separate class).

**Typical count:** 4–15 per image.

### 4.4 `window` — polygon

**What to trace:** The window symbol in the wall (parallel thin lines or glazed rectangle).

**How:**
1. Tight polygon around the window symbol only.
2. Include the wall-break width (the full opening symbol).
3. Each window = **one polygon**, class `window`.

**Do NOT include:** Adjacent wall mass.

**Typical count:** 3–20 per image.

### 4.5 Labeling order per image

```
1. walls (all segments)
2. doors
3. windows
```

Estimated time per image:

| Image | Est. time |
|-------|----------|
| `22177c44...` | 12 min |
| `852f2a15...` | 14 min |
| `ae4cdbb8...` | 16 min |
| Others (train) | 16–22 min |
| `009b1b7a...` | 25 min |
| **Total** | **~3 h** |

---

## 5. CVAT Setup

### 5.1 Create project

1. Open CVAT (local Docker or [app.cvat.ai](https://app.cvat.ai))
2. **Projects → Create new project**
3. Name: `IMPROVED_MODEL_01_PROTOTYPE`
4. Labels — add exactly:

| Name | Type | Color |
|------|------|-------|
| wall | Any | `#FF0000` |
| door | Any | `#00CC00` |
| window | Any | `#0066FF` |

5. **Attribute:** none needed for prototype.

### 5.2 Create task

1. **Tasks → Create task**
2. Name: `prototype_batch_10`
3. Project: `IMPROVED_MODEL_01_PROTOTYPE`
4. **Upload images** from:
   ```
   D:\HCI_interor\IMPROVED_MODEL_1\data\prototype_dataset\images\train\
   D:\HCI_interor\IMPROVED_MODEL_1\data\prototype_dataset\images\val\
   ```
   (Upload as one task of 10 images, or two tasks by split.)

5. **Drawing method:** `By 2 points` + polygon refine, or freehand polygon.
6. Enable **automatic bordering** if available.

### 5.3 CVAT shortcuts

| Action | Key |
|--------|-----|
| Polygon tool | N |
| Save | Ctrl+S |
| Zoom | Mouse wheel |
| Pan | Hold H + drag |
| Delete shape | Delete |
| Next image | Ctrl+F |

---

## 6. Export Format

### 6.1 Export from CVAT

1. Open completed task
2. **Actions → Export task dataset**
3. Format: **`YOLO 1.1`** (Ultralytics-compatible segmentation)
4. Download ZIP

### 6.2 Install labels into project

Extract and copy label files:

```
CVAT export:
  obj_train_data/*.txt   →  data/prototype_dataset/labels/train/
  (val images)         →  data/prototype_dataset/labels/val/
```

**YOLO-seg line format** (one instance per line):

```
<class_id> <x1> <y1> <x2> <y2> <x3> <y3> ...
```

- Coordinates normalized to `[0, 1]`
- `class_id`: wall=0, door=1, window=2

**Verify:** Each `images/train/foo.jpg` must have `labels/train/foo.txt` (same basename).

### 6.3 Class ID mapping in export

If CVAT exports alphabetical labels, verify mapping matches:

```
door   → 1
wall   → 0
window → 2
```

If order differs, run relabel script or fix `dataset.yaml` names order to match export.

---

## 7. YOLO11-seg Training Configuration

### 7.1 Install

```bash
pip install ultralytics>=8.3.0
```

YOLO11 is available in Ultralytics 8.3+ as `yolo11n-seg.pt`.

### 7.2 Training command

```bash
cd D:\HCI_interor\IMPROVED_MODEL_1

yolo segment train \
  model=yolo11n-seg.pt \
  data=data/prototype_dataset/dataset.yaml \
  epochs=50 \
  imgsz=1024 \
  batch=4 \
  patience=15 \
  device=0 \
  project=experiments/prototype \
  name=yolo11n_wall_door_window \
  workers=2 \
  mosaic=1.0 \
  degrees=5.0 \
  scale=0.3 \
  fliplr=0.5 \
  flipud=0.0 \
  hsv_h=0.0 \
  hsv_s=0.0 \
  hsv_v=0.1
```

### 7.3 Recommended hyperparameters (prototype)

| Parameter | Value | Reason |
|-----------|-------|--------|
| `model` | `yolo11n-seg.pt` | Fastest train; 10 images only |
| `imgsz` | `1024` | Preserve thin wall lines |
| `epochs` | `50` | Small data; watch val loss |
| `batch` | `4` | Fits 8GB VRAM at 1024 |
| `patience` | `15` | Early stop if no improvement |
| `mosaic` | `1.0` | Critical for 8 training images |
| `degrees` | `5` | Slight rotation aug only |
| `fliplr` | `0.5` | Floor plans are orientation-sensitive — keep low flip |

### 7.4 Expected training time (RTX GPU)

| GPU | ~Time (50 epochs, 8 images, imgsz=1024) |
|-----|----------------------------------------|
| RTX 3060 12GB | 8–12 min |
| RTX 3070 / 3080 | 5–8 min |
| RTX 4060 / 4070 | 4–7 min |
| RTX 4090 | 3–5 min |

**Note:** With only 8 training images, metrics will be noisy. Prototype goal is **pipeline proof**, not production accuracy.

### 7.5 Minimum viable metrics (prototype)

| Metric | Target |
|--------|--------|
| Training completes | Yes |
| Val mask visible on `22177c44...` | Walls roughly align |
| Inference runs | No crash |
| JSON → IFC | Valid `.ifc` file opens |

---

## 8. Post-Training Pipeline (Hours 5–10)

```
images → YOLO11n-seg predict
       → detection masks / boxes
       → graph_builder (wall centerlines from masks)  [stub OK for demo]
       → BuildingAnalysis JSON (walls + openings only)
       → ifc_adapter → V3 build_detailed_ifc()
       → model.ifc
```

**BuildingAnalysis fields for prototype:**
- `walls[]` — from wall segment detection
- `openings[]` — from door/window detections
- `interiors[]` — empty
- `rooms[]` — empty

---

## 9. Folder Layout (current)

```
data/
├── prototype_classes.yaml
├── prototype_10_images.txt
└── prototype_dataset/
    ├── dataset.yaml
    ├── prototype_manifest.csv
    ├── selection.json
    ├── images/
    │   ├── train/     # 8 images
    │   └── val/       # 2 images
    └── labels/
        ├── train/     # ← paste CVAT export here
        └── val/       # ← paste CVAT export here
```

---

## 10. Checklist Before Training

- [ ] All 10 images annotated in CVAT
- [ ] Exported as YOLO 1.1 segmentation
- [ ] 8 label files in `labels/train/`
- [ ] 2 label files in `labels/val/`
- [ ] Class IDs verified: 0=wall, 1=door, 2=window
- [ ] Spot-check one label file opens in text editor (normalized coords 0–1)
- [ ] `dataset.yaml` path is correct for your machine
- [ ] GPU available: `python -c "import torch; print(torch.cuda.is_available())"`

---

## 11. Known Prototype Limitations

| Limitation | Accept for 10h demo |
|------------|---------------------|
| Only 10 images | Yes — pipeline proof only |
| No room labels | Yes — walls/openings only |
| No scale calibration | Use door-width prior (0.9m) in graph stub |
| Low mAP expected | OK if visual overlay is reasonable on val |
| Graph builder may be stub | Minimum: bbox centers → fake wall segments |

---

## 12. Quick Reference

| Item | Path |
|------|------|
| Images (train) | `data/prototype_dataset/images/train/` |
| Images (val) | `data/prototype_dataset/images/val/` |
| Class config | `data/prototype_classes.yaml` |
| YOLO data yaml | `data/prototype_dataset/dataset.yaml` |
| Full batch (50) | `data/annotation_batch_01/` |
| Clean corpus | `dataset_clean/images/` (do not modify) |

---

*Manual labeling only. No auto-annotation. Training starts after labels are exported.*
