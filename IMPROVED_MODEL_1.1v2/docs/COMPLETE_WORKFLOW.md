# Complete Workflow — IMPROVED_MODEL_1 vs Legacy (`web_file` / `web2`)

**Project:** HCI Interior — Floor Plan AI Training  
**Document type:** End-to-end workflow & comparison guide  
**Audience:** Team, senior review, annotators, ML engineers  
**Last updated:** June 2026  
**Status:** Annotation phase in progress  

---

## Table of contents

1. [Executive summary](#1-executive-summary)  
2. [Project goal](#2-project-goal)  
3. [Legacy workflow (`web_file` / `web2`)](#3-legacy-workflow-web_file--web2)  
4. [IMPROVED_MODEL_1 workflow](#4-improved_model_1-workflow)  
5. [Side-by-side comparison](#5-side-by-side-comparison)  
6. [Phase 1 — detailed steps (current)](#6-phase-1--detailed-steps-current)  
7. [Phased expansion: 7 → 37 classes](#7-phased-expansion-7--37-classes)  
8. [Evaluation vs legacy](#8-evaluation-vs-legacy)  
9. [Future: GUI integration](#9-future-gui-integration)  
10. [Roles, timeline, and milestones](#10-roles-timeline-and-milestones)  
11. [Current status & blockers](#11-current-status--blockers)  
12. [File & path reference](#12-file--path-reference)  

---

## 1. Executive summary

We are building **IMPROVED_MODEL_1** — a YOLO11 instance-segmentation training system that **outperforms** the legacy Floor Plan Model Trainer (`web_file` / `web2`).

| System | Role |
|--------|------|
| **Legacy** (`web_file` / `web2`) | Existing web UI — auto-label, Correct Labels, in-app YOLOv8 training |
| **IMPROVED_MODEL_1** | New pipeline — CVAT annotation, validated YOLO export, YOLO11 training, scripted evaluation |

**Key difference:** Legacy stores polygon-format labels but relies on **mock auto-label + rectangle fixes** and trains **17 collapsed classes** (all room UI types → one `Room` class). IMPROVED_MODEL_1 uses **human CVAT polygons**, **7 focused classes** (phase 1), proper train/val split, and reproducible scripts.

**End state:** Train a better model → plug weights into the same Floor Plan Trainer UI for Test Model → expand classes to match the full Correct Labels list in phases.

---

## 2. Project goal

### Primary objective

Train a **YOLO11n-seg** model on high-quality floor-plan labels that beats legacy on **our** validation images.

### Phase 1 locked classes (IDs 0–6)

| ID | Class | Annotation type |
|----|-------|-----------------|
| 0 | wall | Polygon |
| 1 | door | Polygon |
| 2 | window | Polygon |
| 3 | bedroom | Polygon |
| 4 | living_room | Polygon |
| 5 | kitchen | Polygon |
| 6 | bathroom | Polygon |

### Success criteria (Phase 1)

| ID | Criterion |
|----|-----------|
| M1 | 25 images annotated in CVAT (all 7 classes where visible) |
| M2 | Labels exported, validated, train ≠ val |
| M3 | YOLO11 checkpoint trained (`best.pt`) |
| M4 | Val mAP50 on segmentation **≥ legacy** on comparable classes |
| M5 | Visual QA — walls, doors, windows, rooms look correct on val overlays |

### Out of scope (current phase)

- BIM / IFC / graph / topology (`src/_deferred/`)
- Full 37-class training (deferred to later phases)
- 3-class and 11-class configs (deprecated)

---

## 3. Legacy workflow (`web_file` / `web2`)

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Floor Plan Model Trainer (web_file / web2)                   │
│  http://127.0.0.1:8001                                      │
├─────────────────────────────────────────────────────────────┤
│  [Train]  [Correct Labels]  [Test Model]                    │
└─────────────────────────────────────────────────────────────┘
```

| Component | Location |
|-----------|----------|
| Backend API | `web_file/web/server.py` |
| UI | `web_file/web/index.html` or `web 2/web/index.html` |
| Class registry | `web_file/config/classes.py` → 17 classes |
| UI colors | `CLASS_COLORS` in `index.html` |
| Auto-label | `web_file/web/auto_label.py` |
| Detector | `web_file/logic/detector.py` (mock — returns empty) |

### 3.2 Legacy end-to-end flow

```
Step 1 — Upload / select images
    ↓
Step 2 — Auto-label (heuristic detector + optional OCR/watershed enhancer)
    ↓
Step 3 — Contours converted to YOLO segmentation .txt (polygon coordinates)
    ↓
Step 4 — Correct Labels tab (optional human fix)
         • Remove / relabel instances
         • Draw new region = RECTANGLE only → 4-point polygon
         • web2 UI shows 40+ subtypes (Kitchen, Puja Room, etc.)
         • Training still saves many as single class "Room" (ID 3)
    ↓
Step 5 — dataset.yaml generated (nc: 17)
         • train = val = test = same folder (weak evaluation)
    ↓
Step 6 — Train button → YOLOv8n-seg @ 640px
    ↓
Step 7 — best_gdrive.pt saved
    ↓
Step 8 — Test Model tab → upload image → inference overlay
```

### 3.3 Legacy class taxonomy (17 classes)

| ID | Class |
|----|-------|
| 0 | Wall |
| 1 | Window |
| 2 | Door |
| 3 | Room |
| 4–16 | Slab, Roof, Column, Beam, Stair, Railing, CurtainWall, Furniture, Covering, LightFixture, ElectricAppliance, FlowTerminal, EnergyConversionDevice |

**Critical gap:** web2 Correct Labels dropdown shows Living Room, Kitchen, Bedroom, etc., but `value="Room"` for all — **subtype is not a separate YOLO class** in training files.

### 3.4 Legacy limitations

| Issue | Impact |
|-------|--------|
| Mock detector | Often zero or wrong labels |
| Rectangle-only manual draw | Poor wall/door/window boundaries |
| Single `Room` class | No room-type learning |
| Walls rarely auto-labeled | Weak structure detection |
| train = val = test | Unreliable metrics |
| No pre-train label QC | Trains on bad labels |
| YOLOv8n @ 640 | Less detail on thin lines |
| 17 sparse classes on small data | Many classes under-represented |

---

## 4. IMPROVED_MODEL_1 workflow

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  IMPROVED_MODEL_1 — Training pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  CVAT (annotation)  →  Scripts (QC + train)  →  Evaluate  │
│  Future: plug best.pt into Floor Plan Trainer Test tab      │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 End-to-end flow (Phase 1)

```
┌──────────────────┐
│ 1. DATA STAGING  │  25 images in prototype_7_batch/
│                  │  20 train / 5 val (manifest.csv)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 2. CVAT SETUP    │  Docker: D:\HCI_interor\cvat
│                  │  URL: http://localhost:9000
│                  │  Project: IMPROVED_MODEL_1_7Class_Seg
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 3. ANNOTATION    │  Human polygons per rulebook
│                  │  Order: wall → door → window → rooms
│                  │  Classes: 7 only (phase 1)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 4. CVAT EXPORT   │  Format: YOLO 1.1 segmentation
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 5. IMPORT        │  export_cvat_to_yolo.py
│                  │  Remap CVAT class order → IDs 0–6
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 6. VALIDATION    │  validate_labels.py
│                  │  check_dataset_integrity.py
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 7. TRAINING      │  train.py → YOLO11n-seg @ 1024
│                  │  Output: runs/prototype_7_seg/weights/best.pt
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 8. EVALUATION    │  evaluate.py
│                  │  Per-class mAP + optional legacy compare
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 9. ITERATION     │  Fix annotation errors → retrain
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 10. DEPLOY UI    │  Load best.pt in web2 Test Model tab
│     (future)     │  Expand classes in later phases
└──────────────────┘
```

### 4.3 Active configuration

| Item | Path / value |
|------|----------------|
| Class config | `data/prototype_7_classes.yaml` |
| Dataset root | `data/prototype_7_batch/` |
| dataset.yaml | `data/prototype_7_batch/dataset.yaml` |
| Annotation rules | `docs/CANONICAL_ANNOTATION_RULEBOOK.md` |
| CVAT guide | `docs/CVAT_OVERVIEW.md` |

### 4.4 Dataset layout

```
data/prototype_7_batch/
├── images/
│   ├── train/          # 20 images (manifest ranks 1–20)
│   └── val/            # 5 images (ranks 21–25)
├── labels/
│   ├── train/          # one .txt per image (after CVAT export)
│   └── val/
├── manifest.csv        # rank, filename, split
└── dataset.yaml        # nc: 7, paths, class names
```

### 4.5 Training defaults

| Parameter | Value |
|-----------|-------|
| Model | `yolo11n-seg.pt` |
| Image size | 1024 |
| Epochs | 50 |
| Batch | 4 |
| Patience (early stop) | 15 |
| Run name | `prototype_7_seg` |

---

## 5. Side-by-side comparison

### 5.1 Workflow comparison

| Stage | Legacy (`web_file` / `web2`) | IMPROVED_MODEL_1 |
|-------|------------------------------|------------------|
| **Image source** | Upload in web UI | `prototype_7_batch/` (+ ~314 corpus for scale-up) |
| **Annotation tool** | Correct Labels (in-app) | **CVAT** (http://localhost:9000) |
| **Label origin** | Mock auto-label + fixes | **Human-first** polygons |
| **Manual draw** | Rectangle → 4-point polygon | **Free polygon** |
| **Class list UI** | 40+ options (web2) | 7 active (phase 1) |
| **Classes in training** | 17 (rooms collapsed) | **7 distinct** |
| **Export** | Direct to dataset folder | CVAT export → import script |
| **Label validation** | None | `validate_labels.py` + integrity check |
| **Train/val split** | Same folder | **20 train / 5 val** |
| **Training** | Web UI button | `scripts/train.py` |
| **Model** | YOLOv8n-seg | **YOLO11n-seg** |
| **Resolution** | 640px | **1024px** |
| **Evaluation** | In-app metrics (unreliable) | `evaluate.py` + legacy compare |
| **Reproducibility** | Low | **High** (scripted pipeline) |

### 5.2 Annotation comparison

| Aspect | Legacy | IMPROVED_MODEL_1 |
|--------|--------|------------------|
| Wall labeling | Class exists; rarely auto-generated | **Required** every image |
| Room semantics | One `Room` class | **4 room types** separate from walls |
| Door/Window IDs | Window=1, Door=2 | door=1, window=2 |
| Subtype in UI → training | **No** (collapsed) | **Yes** (label = class name) |
| QC before train | No | **Yes** |

### 5.3 Why IMPROVED_MODEL_1 should beat legacy

| Lever | Effect |
|-------|--------|
| Better ground truth | Human polygons vs mock/heuristic labels |
| Semantic correctness | Walls ≠ room perimeters; distinct room classes |
| Class focus | 7 classes on 25 images vs 17 sparse classes |
| Training discipline | Honest val split + pre-train gates |
| Newer model + resolution | YOLO11 @ 1024 vs YOLOv8n @ 640 |

---

## 6. Phase 1 — detailed steps (current)

### Step 0 — Prerequisites

```powershell
# Start Docker Desktop, then CVAT
cd D:\HCI_interor\cvat
docker compose up -d

# Open browser
# http://localhost:9000
```

Create admin if needed:

```powershell
docker exec -it cvat_server bash -ic "python3 ~/manage.py createsuperuser"
```

Install Python deps for IMPROVED_MODEL_1:

```powershell
cd D:\HCI_interor\IMPROVED_MODEL_1
pip install -r requirements.txt
```

---

### Step 1 — CVAT project setup

1. Log in to CVAT at **http://localhost:9000**
2. **Projects** → **Create new project**
3. Name: `IMPROVED_MODEL_1_7Class_Seg`
4. Add labels (type: **Polygon**):

| Label | Suggested color |
|-------|-----------------|
| wall | #FF0000 |
| door | #00CC00 |
| window | #0066FF |
| bedroom | #FFE066 |
| living_room | #66CCFF |
| kitchen | #FF9999 |
| bathroom | #66CCCC |

5. **Create task** → upload images from:
   - `D:\HCI_interor\IMPROVED_MODEL_1\data\prototype_7_batch\images\train`
   - (Optional separate task for `images\val`)

---

### Step 2 — Annotate (follow rulebook)

Read: `docs/CANONICAL_ANNOTATION_RULEBOOK.md`

**Annotation order per image:**

1. **wall** — closed polygon along wall thickness (not room perimeter)  
2. **door** — opening symbol only (if visible)  
3. **window** — opening symbol only (if visible)  
4. **bedroom**, **living_room**, **kitchen**, **bathroom** — interior floor polygons (if identifiable)  

**Rules:**

- Minimum 4 vertices per polygon  
- Zoom 200–400% for doors/windows  
- One polygon per instance  
- Val set (5 images): 100% peer review  

**Estimated time:** 20–30 hours for 25 images (first pass)

---

### Step 3 — Export from CVAT

1. Open completed task  
2. **Menu** → **Export task dataset**  
3. Format: **YOLO 1.1 segmentation**  
4. Save zip to a known folder (e.g. `Downloads/cvat_export/`)

---

### Step 4 — Import into project batch

```powershell
cd D:\HCI_interor\IMPROVED_MODEL_1

# Extract export zip first, then:
python scripts/export_cvat_to_yolo.py path\to\cvat\export\folder --validate
```

This script:

- Copies/remaps label files into `labels/train/` and `labels/val/`  
- Maps CVAT class order to locked IDs 0–6  
- Runs validation if `--validate` is set  

---

### Step 5 — Validate dataset

```powershell
python scripts/validate_labels.py
python scripts/check_dataset_integrity.py
```

**Pass criteria:**

- 25 label `.txt` files (matching images)  
- All class IDs in 0–6  
- No empty coordinate lines  
- train and val folders both populated  

---

### Step 6 — Train YOLO11

```powershell
python scripts/train.py --data data/prototype_7_batch/dataset.yaml
```

**Output:** `runs/prototype_7_seg/weights/best.pt`

If PyTorch DLL errors occur on Windows, fix CUDA/CPU torch install before training.

---

### Step 7 — Evaluate

```powershell
python scripts/evaluate.py --weights runs/prototype_7_seg/weights/best.pt --data data/prototype_7_batch/dataset.yaml
```

Optional legacy comparison (after training legacy on same images):

```powershell
python scripts/evaluate.py --weights runs/prototype_7_seg/weights/best.pt --compare-legacy path\to\legacy\best.pt
```

---

### Step 8 — Visual QA

- Run inference on val images  
- Overlay predicted masks vs ground truth  
- Fix annotation errors on failure cases  
- Retrain if needed  

---

### Step 9 — Regenerate splits (if manifest changes)

```powershell
python scripts/split_batch_from_manifest.py --write-dataset-yaml
```

---

## 7. Phased expansion: 7 → 37 classes

Senior requirement: train all types shown in Correct Labels (Living Room, Kitchen, Puja Room, furniture, MEP, etc.). This is **phased**, not day one.

```
PHASE 1 (NOW) — 7 classes
  wall, door, window, bedroom, living_room, kitchen, bathroom
  → First model, beat legacy on val set

PHASE 2 — + structural
  column, stair

PHASE 3 — + room types (align with Correct Labels list)
  master_bedroom, dining_room, toilet, balcony, utility, corridor, ...

PHASE 4 — + furniture
  bed, sofa, wardrobe, dining_table, tv_unit, cabinet, ...

PHASE 5 — + fixtures & appliances (full 37)
  wc, wash_basin, shower, stove, refrigerator, ...
```

**Per-phase workflow (repeat):**

1. Update active YAML config  
2. Add CVAT labels for new classes  
3. Annotate (incremental — don’t re-annotate correct old labels unless wrong)  
4. Export → import → validate  
5. **Fine-tune** from previous `best.pt` (faster than scratch)  
6. Evaluate vs previous phase + legacy  
7. Senior sign-off before next phase  

**Reference taxonomy:** `data/classes.yaml` (37 production IDs)  
**Prototype → production map:** `data/prototype_7_classes.yaml` → `production_id_map`

---

## 8. Evaluation vs legacy

### 8.1 Fair comparison rules

| Rule | Why |
|------|-----|
| Same val images | Apples-to-apples |
| Map legacy classes to ours where possible | Wall, Door, Window comparable; legacy `Room` vs our 4 room classes needs careful mapping |
| Report **segmentation** mAP (mask), not box only | Both systems are seg models |
| Visual overlay on val set | Numbers alone can mislead on floor plans |

### 8.2 Class mapping for comparison

| IMPROVED_MODEL_1 | Legacy | Comparable? |
|------------------|--------|-------------|
| wall (0) | Wall (0) | Yes |
| door (1) | Door (2) | Yes (different ID) |
| window (2) | Window (1) | Yes (different ID) |
| bedroom, living_room, kitchen, bathroom | Room (3) | Partial — legacy is one class |

Phase 1 comparison focus: **wall, door, window** seg mAP + visual room quality.

### 8.3 Success definition (Phase 1)

- IMPROVED_MODEL_1 val mAP50 (seg) **≥ legacy** on wall + door + window  
- Room polygons visually better on val overlays  
- Documented comparison report for senior  

---

## 9. Future: GUI integration

CVAT does not replace the Floor Plan Trainer UI permanently.

### Planned integration

| Phase | Feature |
|-------|---------|
| **Now** | CVAT standalone at localhost:9000 |
| **Next** | **Annotate in CVAT** button in web GUI → open task → auto-import labels |
| **After train** | Load `best.pt` in **Test Model** tab |
| **Later** | CVAT REST API — upload, sync classes, train from one app |

### Senior alignment

> “User marks area as per list → same used for training.”

- **Legacy today:** UI list ≠ training classes (collapsed)  
- **IMPROVED_MODEL_1:** CVAT label name = YOLO class = model output  
- **Future GUI:** Same class list as Correct Labels, fed from `classes.yaml`  

---

## 10. Roles, timeline, and milestones

### Roles

| Role | Responsibilities |
|------|------------------|
| **Annotator** | CVAT polygons per rulebook |
| **Reviewer** | Val set QC, spot-check train set |
| **ML engineer** | Export, validate, train, evaluate, document |
| **Senior / PM** | Approve phase gates, class expansion |

### 4-week timeline (Phase 1)

| Week | Focus | Deliverable |
|------|-------|-------------|
| **1** | CVAT annotation + export | 25 validated label files |
| **2** | First YOLO11 train | `best.pt` checkpoint |
| **3** | Evaluate vs legacy, fix labels | Comparison report |
| **4** | Scale to 50 images (`annotation_batch_01/`) | Stronger baseline |

### Milestone checklist

- [ ] CVAT project created (`IMPROVED_MODEL_1_7Class_Seg`)
- [ ] 25 images annotated (7 classes)
- [ ] Labels exported and imported
- [ ] `validate_labels.py` passes
- [ ] `check_dataset_integrity.py` passes
- [ ] `train.py` completes
- [ ] `evaluate.py` report generated
- [ ] Legacy comparison documented
- [ ] Senior sign-off on Phase 1

---

## 11. Current status & blockers

| Item | Status |
|------|--------|
| `prototype_7_batch/` images | ✅ 25 (20 train / 5 val) |
| `dataset.yaml` | ✅ |
| CVAT Docker | ✅ Running at http://localhost:9000 |
| CVAT annotation | 🔄 In progress |
| Label files in batch | ❌ 0 (pending export) |
| First YOLO11 train | ⏳ Blocked on labels |
| Legacy comparison | ⏳ After first train |

**Critical path:** CVAT annotation → export → validate → train → evaluate

---

## 12. File & path reference

### IMPROVED_MODEL_1

| Path | Purpose |
|------|---------|
| `data/prototype_7_classes.yaml` | Active 7-class training config |
| `data/prototype_7_batch/` | Active dataset |
| `data/classes.yaml` | Full 37-class taxonomy (future) |
| `docs/CANONICAL_ANNOTATION_RULEBOOK.md` | Annotation rules |
| `docs/CVAT_OVERVIEW.md` | What is CVAT (stakeholder guide) |
| `docs/ANNOTATION_EXECUTION_PLAN.md` | Short execution steps |
| `scripts/export_cvat_to_yolo.py` | CVAT → batch import |
| `scripts/validate_labels.py` | Label QC |
| `scripts/check_dataset_integrity.py` | Dataset structure QC |
| `scripts/train.py` | YOLO11 training |
| `scripts/evaluate.py` | mAP + legacy compare |
| `scripts/split_batch_from_manifest.py` | Regenerate train/val split |

### Legacy

| Path | Purpose |
|------|---------|
| `web_file/web/server.py` | Legacy API + train + auto-label |
| `web_file/web/index.html` | Trainer UI (Correct Labels) |
| `web 2/web/index.html` | Extended UI + IFC subtypes |
| `web_file/config/classes.py` | 17-class IDs |
| `web_file/web/auto_label.py` | Contour → YOLO seg |
| `web_file/logic/detector.py` | Mock heuristic detector |

### CVAT

| Path | Purpose |
|------|---------|
| `D:\HCI_interor\cvat\` | CVAT Docker stack |
| `docker compose up -d` | Start CVAT |
| http://localhost:9000 | CVAT web UI |

---

## Quick command reference

```powershell
# --- CVAT ---
cd D:\HCI_interor\cvat
docker compose up -d
# Browser: http://localhost:9000

# --- Import labels ---
cd D:\HCI_interor\IMPROVED_MODEL_1
python scripts/export_cvat_to_yolo.py <cvat_export_dir> --validate
python scripts/check_dataset_integrity.py

# --- Train & evaluate ---
python scripts/train.py --data data/prototype_7_batch/dataset.yaml
python scripts/evaluate.py --weights runs/prototype_7_seg/weights/best.pt
```

---

## Related documents

| Document | Link |
|----------|------|
| Documentation index | [README.md](./README.md) |
| CVAT overview | [CVAT_OVERVIEW.md](./CVAT_OVERVIEW.md) |
| Annotation rulebook | [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) |
| HLD | [HLD.md](./HLD.md) |
| Class taxonomy | [CLASS_TAXONOMY.md](./CLASS_TAXONOMY.md) |
| Development roadmap | [DEVELOPMENT_ROADMAP.md](./DEVELOPMENT_ROADMAP.md) |

---

*End of complete workflow document — IMPROVED_MODEL_1 vs legacy.*
