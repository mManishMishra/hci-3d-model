# Architecture Analysis — HCI Interior / Floor Plan → BIM Platform

**Document:** Phase 1 deliverable  
**Location:** `D:\HCI_interor\IMPROVED_MODEL_1\docs\`  
**Date:** 2026-06-09  
**Scope:** Analysis of four reference implementations. No code changes to existing projects.

---

## Executive Summary

The HCI Interior platform has evolved along **two parallel tracks** that were never fully integrated:

| Track | Location | Paradigm | Maturity |
|-------|----------|----------|----------|
| **Training / Vision** | `web_file/` | YOLOv8 instance segmentation + human correction UI | Orchestration complete; **CV labeling pipeline is stubbed** |
| **IFC Generation** | `floorplan_ifc_ai/` → `latest_interior/` → `latest_interior_v1/` | Gemini vision → Pydantic JSON → IfcOpenShell IFC4 | **V3 is production-shaped** for BIM output; perception is LLM-only |

The current end-to-end system is:

```
Floor Plan Image → Gemini → BuildingAnalysis JSON → build_detailed_ifc() → IFC4
```

The target system for `IMPROVED_MODEL_1` is:

```
Floor Plan Image → Vision Model → Detections → Building Graph → Topology Validation → BuildingAnalysis JSON → IFC4
```

**Key architectural insight:** V3 (`latest_interior_v1`) already defines a strong **downstream contract** (`BuildingAnalysis` + `ifc_properties.py` + `build_detailed_ifc()`). The improved training pipeline should **produce that same JSON** from deterministic geometry, not replace the IFC compiler on day one.

---

## Workspace Map

```
D:\HCI_interor\
├── web_file/                  # Old training module (YOLO-seg + web UI)
├── floorplan_ifc_ai/          # IFC Generation V1 (monolith prototype)
├── latest_interior/           # IFC Generation V2 (property-rich compiler)
├── latest_interior_v1/        # IFC Generation V3 (most advanced)
├── gdrive_dataset/            # Dataset stub (dataset.yaml only, images elsewhere)
└── IMPROVED_MODEL_1/          # NEW — improved training architecture (this project)
```

---

## 1. `web_file` — Old Training Module

### 1.1 What It Does

A **self-contained floor-plan model training web application** that:

1. Ingests images from Google Drive or manual upload
2. Auto-labels images into YOLO segmentation format
3. Trains YOLOv8-nano segmentation (`yolov8n-seg.pt`) on a 17-class IFC-inspired taxonomy
4. Provides a correction UI for human label editing
5. Supports fine-tuning, model versioning, and naive checkpoint merging
6. Runs inference with heuristic fallback when the model returns zero detections

**Entry point:** `web_file/web/server.py` (FastAPI on port 3000)  
**Frontend:** `web_file/web/index.html` (~2,900 lines, single-page app)  
**Training orchestration:** `web_file/web/auto_label.py` + Ultralytics API in `server.py`

### 1.2 Directory Structure

```
web_file/
├── config/
│   └── classes.py              # 17-class IFC taxonomy (CLASS_IDS)
├── logic/
│   ├── detector.py             # MOCK — returns empty detections
│   ├── floor_plan_analyzer.py  # MOCK — passthrough
│   ├── room_text_mapper.py     # MOCK — no OCR
│   └── image_metadata.py       # JSON sidecar metadata (minimal)
└── web/
    ├── server.py               # Monolithic FastAPI backend (~1,510 lines)
    ├── auto_label.py           # Contour → YOLO-seg conversion
    └── index.html              # Train / Correct / Test tabs
```

### 1.3 Dataset Handling

| Aspect | Implementation |
|--------|----------------|
| **Root path** | `{PROJECT_ROOT}/gdrive_dataset/` |
| **Raw images** | `images_raw/` |
| **Training set** | `images/train/` + `labels/train/*.txt` |
| **Visualizations** | `marked/*_labelled.jpg`, `*_pre_label.jpg`, `*_post_label.jpg` |
| **Metadata** | `metadata/{stem}.json` |
| **Config** | `dataset.yaml` (generated at auto-label time) |
| **Ingestion** | GDrive folder ID `18IThRKRGUHFXnSiMtJlhqHSphDIuphNk` via `gdown`, or `POST /api/upload` |
| **Formats** | JPG, PNG, BMP, TIFF, WebP, SVG (SVG rasterized via `cairosvg`) |

**Critical flaw:** `train`, `val`, and `test` all point to the **same folder** (`images/train`). Validation metrics are optimistically biased.

The local `gdrive_dataset/dataset.yaml` at workspace root references `C:\Users\DELL\Downloads\gdrive_dataset` — a path from another machine. No training images exist in-repo.

### 1.4 Training Workflow

```
images_raw → auto_label (detector + OCR + watershed) → labels/train/*.txt
           → dataset.yaml
           → YOLOv8n-seg.train(epochs, batch, imgsz=640)
           → gdrive_dataset/runs/train/weights/best.pt
           → copied to best_gdrive.pt
```

| Mode | API | Notes |
|------|-----|-------|
| Full train | `POST /api/train` | From `yolov8n-seg.pt`, default 50 epochs, batch 4 |
| Fine-tune | `POST /api/train_from_corrections` | `lr0=0.0005`, `freeze=10`, `close_mosaic=0` |
| Merge | `POST /api/merge_models` | Naive weight averaging (fragile) |

Progress is streamed via SSE (`/api/stream`). Device selection: CUDA → MPS → CPU.

### 1.5 Data Preprocessing

- **Minimal custom preprocessing.** Images loaded with `cv2.imread`; Ultralytics handles augmentation during training.
- **Intended but stubbed:** caption removal, OCR text seeds, watershed room splitting (`analyse_floor_plan`, `analyse_image`).
- **Label export:** polygon contours normalized to [0,1] for YOLO-seg format.

### 1.6 Annotation Strategy

**Format:** YOLO instance segmentation (polygon per line), **not COCO JSON**.

```
<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>
```

**17-class taxonomy** (`config/classes.py`):

| ID | Class | Auto-label source |
|----|-------|-------------------|
| 0 | Wall | — (never pseudo-labeled) |
| 1 | Window | `windows` |
| 2 | Door | `doors` |
| 3 | Room | `rooms` |
| 4–10 | Slab, Roof, Column, Beam, Stair, Railing, CurtainWall | Stair only |
| 11 | Furniture | `furniture` |
| 12–16 | Covering, LightFixture, ElectricAppliance, FlowTerminal, EnergyConversionDevice | FlowTerminal only |

**Human correction APIs:** remove/relabel, resize bbox (axis-aligned rectangle), draw new region, save/revert.

**Metadata sidecars** support OCR and Gemini provenance, but `metadata_choice` UI parameter (`use` / `local` / `gemini`) is **accepted but never read** in the auto-label worker.

### 1.7 Model Architecture

- **Framework:** Ultralytics YOLOv8-nano segmentation (`yolov8n-seg.pt`)
- **Task:** Instance segmentation (mask + box + class heads)
- **Classes:** `nc=17`, reconfigured via `dataset.yaml`
- **No custom backbone, neck, or loss** — stock Ultralytics defaults
- **Inference:** `model(img, imgsz=640, conf=0.1)` with mask threshold 0.5

### 1.8 Strengths

1. **Complete training UX** — Train → Correct → Test → Fine-tune workflow is coherent and production-minded.
2. **IFC-aligned class taxonomy** — 17 classes map cleanly to BIM element types; good target for detection heads.
3. **YOLO-seg conversion utilities** — `contour_to_yolo_seg`, `draw_labelled_image`, label round-trip from disk are solid.
4. **Fine-tune hyperparameters** — Sensible small-dataset settings (frozen backbone, low LR, no mosaic).
5. **Model version registry** — Scan and activate checkpoints across run directories.
6. **Real-time training progress** — SSE callbacks without WebSocket complexity.
7. **Label correction CRUD** — Full polygon label editing with disk persistence.
8. **SVG support pattern** — Important for vector-origin floor plans.

### 1.9 Weaknesses

| Severity | Issue |
|----------|-------|
| **Critical** | `detector.py`, `floor_plan_analyzer.py`, `room_text_mapper.py` are **mocks returning empty data** — auto-label skips every image |
| **Critical** | `corrected_rooms` referenced but undefined in `_autolabel_worker` → `NameError` if labeling ever produced results |
| **High** | No train/val/test split — metrics unreliable |
| **High** | No `requirements.txt` — environment not reproducible |
| **High** | Monolithic `server.py` (~1,510 lines) + inline SPA (~2,900 lines) — hard to maintain |
| **Medium** | BBox corrections degrade polygons to axis-aligned rectangles |
| **Medium** | Only 6 of 17 classes are pseudo-labeled; Wall never auto-labeled |
| **Medium** | In-memory `_analysis` stores base64 JPEGs — memory-heavy at scale |
| **Medium** | Model merge is naive weight arithmetic, not SWA or ensemble |
| **Low** | `metadata_choice` dead code; Gemini path is placeholder |
| **Low** | Revert API expects `.bak` files that are never created |

### 1.10 Reusable Components

| Component | Path | Reuse in IMPROVED_MODEL_1 |
|-----------|------|---------------------------|
| Class taxonomy | `config/classes.py` | **Adopt as detection class registry**; align with BIM schema |
| YOLO-seg label I/O | `web/auto_label.py` | **Reuse format** for wall/door/window/room masks |
| Dataset folder convention | `server.py` paths | **Extend** with proper val/test splits |
| Fine-tune hyperparameters | `_finetune_worker` | **Reference** for small-dataset training config |
| Label correction UX patterns | `index.html` + correction APIs | **Inspire** annotation tool design |
| Metadata sidecar pattern | `logic/image_metadata.py` | **Extend** with provenance, scale, graph version |

### 1.11 Components to Replace

| Component | Replacement |
|-----------|-------------|
| Mock detector / analyzer / OCR | Dedicated preprocessing + detection models (walls as lines/masks, symbol detectors) |
| Monolithic server + inline SPA | Modular `training/` package + optional thin API |
| Train=val split | Stratified k-fold or holdout with `images/val`, `labels/val` |
| Gemini placeholder in autolabel | Graph builder producing `BuildingAnalysis`, not LLM |
| YOLO-only architecture | Multi-head or multi-stage: wall segmentation + opening detection + OCR branch |
| In-memory state | File-based or SQLite job store |

---

## 2. `floorplan_ifc_ai` — IFC Generation Version 1

### 2.1 What It Does

A **minimal single-file prototype** (~184 lines in `main.py`) demonstrating:

```
Floor plan image → Gemini structured JSON → IfcOpenShell IFC4 file
```

### 2.2 Directory Structure

```
floorplan_ifc_ai/
├── main.py                      # Entire application
├── 1_BHK_HOUSE.jpg              # Sample input
├── 1_BHK_Detailed_Cache.json    # Cached extraction
├── 1_BHK_Detailed.ifc           # Sample output
└── venv/                        # Bundled Python 3.11.7 environment
```

No `requirements.txt`, README, tests, or package layout.

### 2.3 Gemini Usage

| Setting | Value |
|---------|-------|
| Model | `gemini-3-flash-preview` |
| Auth | `GEMINI_API_KEY` env var |
| Input | Raw image bytes, MIME hardcoded to `image/jpeg` |
| Output | `response_mime_type="application/json"`, `response_schema=BuildingAnalysis` |
| Temperature | 0.1 |
| Prompt | ~3 sentences: centerline walls, openings with host wall, furniture/sanitary/appliances |

**No retry, no error handling** despite importing `APIError`, `ServerError`, `ClientError`.

### 2.4 JSON Schema (V1)

```python
WallData:        wall_id, start_pt, end_pt, thickness (no height, no unit)
OpeningComponent: id, type, location_pt, width, height, parent_wall_id
InteriorComponent: id, category, location_pt, dimensions
BuildingAnalysis: building_name, walls[], openings[], interiors[]
```

### 2.5 IFC Generation Flow

1. Create IFC4 file with Project → Site → Building → Storey hierarchy
2. Walls: centerline placement + extruded rectangle, **fixed 3.0 m height**, plain `IfcWall`
3. Openings: `IfcDoor` / `IfcWindow` at location — **`parent_wall_id` never used**, no voids
4. Interiors: category-mapped entities with extruded box geometry
5. `IfcRelContainedInSpatialStructure` aggregates all elements

### 2.6 Strengths

1. **End-to-end proof of concept** in one readable file
2. **Pydantic schema enforcement** reduces parsing errors vs free-text JSON
3. **Centerline wall model** — correct BIM abstraction
4. **JSON cache layer** decouples expensive vision from IFC iteration
5. **Rich element taxonomy** in a single Gemini pass
6. **Valid IFC4 spatial hierarchy**

### 2.7 Weaknesses

| Issue | Impact |
|-------|--------|
| **Unit mismatch** | IFC declares metres; cache coordinates are image pixels (~20–980 range) → building ~1000 m wide |
| **Openings not hosted** | Doors/windows float; walls are solid through openings |
| **Doors/windows lack geometry** | Metadata only; invisible in most viewers |
| **Fixed 3 m wall height** | No per-wall or multi-storey support |
| **No rooms (`IfcSpace`)** | No spatial program or area schedules |
| **No property sets** | Poor Revit/ArchiCAD interoperability |
| **Cache defaults on** | Stale wrong JSON silently reused |
| **Monolithic, no tests** | Hard to evolve or validate |

### 2.8 Reusable vs Replaceable

| Reuse | Replace |
|-------|---------|
| `BuildingAnalysis` shape (extended in later versions) | `analyze_floor_plan_detailed()` — entire Gemini call |
| JSON cache workflow | `gemini-3-flash-preview` model choice |
| Centerline wall extrusion math (with unit fix) | Hardcoded JPEG MIME type |
| Category → IFC entity mapping | Unit handling (none in V1) |
| CLI argument structure | Opening compiler (placement-only) |

---

## 3. `latest_interior` — IFC Generation Version 2

### 3.1 What It Does

Evolution of V1 into a **two-file property-rich BIM compiler**:

```
Image → Gemini 2.5 Flash → BuildingAnalysis JSON → build_detailed_ifc() + ifc_properties.py → IFC4
```

**Files:**
- `latest_interior/latest_interior/automated_bim_v4_connected.py` (~614 lines)
- `latest_interior/latest_interior/ifc_properties.py` (~468 lines)
- Test asset: `model_2.svg` (CubiCasa-format vector floor plan)

### 3.2 Improvements Over V1

| Area | V1 | V2 |
|------|----|----|
| Architecture | 1 file | Extractor + property schema module |
| Model | `gemini-3-flash-preview` | `gemini-2.5-flash` |
| Units | Raw pixels | `_to_meters()`, `_normalize_point()`, per-field `unit` |
| Wall entity | `IfcWall`, fixed 3 m | `IfcWallStandardCase`, per-wall height |
| Properties | None | Full Pset pipeline, ArchiCAD compatibility |
| Quantities | None | `BaseQuantities` + ArchiCAD quantity sets |
| Error handling | Minimal | API error handling with exit codes |
| Prompt | 3 sentences | Multi-section geometry + proportion guidance |
| MIME | Hardcoded JPEG | Extension-based map (SVG still sent as JPEG) |

### 3.3 JSON Schema Extensions (V2)

Added to all geometry types:
- `unit: str = "m"` on walls, openings, interiors
- `height: float = 3.0` on `WallData`
- `ElementProperty` not yet present (added in V3)

Observed cache (`1_BHK_Detailed_Cache.json`): coordinates in metres, realistic dimensions.

### 3.4 IFC Workflow (V2)

Same spatial hierarchy as V1, plus:
- `assign_default_ifc_properties()` from `IFC_SCHEMA` dict
- `create_ifc_property_set()`, `create_ifc_quantity_set()`
- `normalize_opening_type()` for arches/portals
- Dynamic `ifc_properties.py` discovery via `importlib`

**Still missing in V2:**
- `IfcOpeningElement` / `IfcRelVoidsElement` — openings don't cut walls
- `IfcSpace` rooms — schema defined in `ifc_properties.py` but never instantiated
- `IfcSlab` floors
- Interior placement is corner-origin (can overlap walls)

### 3.5 Regressions / Gaps vs V1

V2 is overwhelmingly an improvement. Remaining gaps are shared with V1 plus:
- **Slower and costlier** (richer prompt, stable model)
- **Trusts AI for scale** — no dimension-line parsing or pixel→metre calibration
- **SVG sent as JPEG MIME** — loses vector semantics (though Gemini may still parse visually)

### 3.6 Reusable Components

| Component | Reuse |
|-----------|-------|
| `ifc_properties.py` | **Core BIM semantics layer** |
| `build_detailed_ifc()` | **IFC compiler** (with V3 upgrades) |
| `_to_meters`, `_normalize_point` | **Unit normalization** |
| `BuildingAnalysis` Pydantic models | **Interchange contract** |
| Cache + `--force` CLI pattern | **Experiment iteration** |

### 3.7 Components to Replace for Vision Pipeline

- Entire `analyze_floor_plan_detailed()` function
- All Gemini prompts and `GenerateContentConfig`
- Single-pass extraction (replace with detection + graph + validation)

**Important opportunity:** `model_2.svg` contains structured CubiCasa elements (`Space`, `Wall`, `Door`, `Window`, `FixedFurnitureSet`) with metre labels. A **vector parser** could produce `BuildingAnalysis` without any LLM — useful as pseudo-ground-truth for training data generation.

---

## 4. `latest_interior_v1` — IFC Generation Version 3 (Most Advanced)

### 4.1 What It Does

The **current production-shaped LLM→BIM pipeline** with extraction guardrails, rich metadata, and partial opening topology.

**Files:**
- `latest_interior_v1/latest_interior_v1/automated_bim_v4_connected.py` (~1,341 lines)
- `latest_interior_v1/latest_interior_v1/ifc_properties.py` (~664 lines)
- `run.sh`, `model_2_Detailed_Cache.json`, `output.ifc`

### 4.2 Gemini Extraction (V3)

| Setting | Value |
|---------|-------|
| Model | `gemini-2.5-flash` |
| Temperature | `0.0` |
| Max output tokens | `8192` |
| Schema | Extended `BuildingAnalysis` with `ElementProperty`, materials, colors |

**Prompt design** (`_build_extraction_prompt()`):
1. Walls — centerlines, split at corners/T-junctions, exterior vs interior thickness
2. Openings — doors/windows/arches, `parent_wall_id`, operation types, materials
3. Interiors — typed enums (BED, SOFA, WC, etc.), dimensions, property rows
4. Classification examples with sample property rows

**Plan-aware augmentation:** `_infer_bhk_count()` from filename → `_expected_minimum_counts()` → completeness gate.

**Retry logic:**
1. First extraction
2. If counts below BHK-derived thresholds → retry with stricter prompt
3. Keep result if `_extraction_score()` improves
4. Hard fail unless `--allow-low-detail`

**Not validated geometrically:** wall connectivity, opening-on-wall placement, scale consistency, duplicate elements.

### 4.3 JSON Schema (V3 — Target Contract)

```python
ElementProperty:  name, value, pset (optional)
OpeningComponent: id, type, location_pt, width, height, parent_wall_id,
                  operation_type, material, color, properties[], unit
InteriorComponent: id, category, type, location_pt, dimensions,
                   material, color, properties[], unit
WallData:         wall_id, start_pt, end_pt, thickness, height, unit
BuildingAnalysis: building_name, walls[], openings[], interiors[]
```

`@field_validator` normalizes Gemini's flexible property dicts into `ElementProperty` lists.

### 4.4 IFC Creation (V3 Upgrades)

| Feature | V2 | V3 |
|---------|----|----|
| Opening topology | Standalone entities | `IfcOpeningElement` + `IfcRelVoidsElement` + `IfcRelFillsElement` |
| Interior placement | Corner-origin box | Center-origin + AABB wall-collision shrink |
| Furniture class | `IfcFurnishingElement` | `IfcFurniture` with `PredefinedType` |
| Type resolution | Hardcoded switch | `COMPONENT_TYPE_MAP`, `OPENING_TYPE_MAP` |
| Materials/colors | None | `assign_material()`, `assign_surface_style()` |
| Property filtering | All Psets | `pset_names` allowlist per component type |

**Gap:** Opening void relationships exist but **wall solids are not boolean-cut** — viewers may not show physical openings.

**Still absent:** `IfcSpace` rooms, `IfcSlab`, multi-storey, geometric validation layer.

### 4.5 Current Bottlenecks

1. **LLM as sole perception engine** — all geometry from one multimodal call
2. **8192 token ceiling** — large plans risk truncation
3. **No scale calibration** — coordinates assumed metric with no pixel tie
4. **Fragile `parent_wall_id`** — string match only, no snap-to-wall validation
5. **No room graph** — walls exist independently
6. **API cost/latency** — retry doubles Gemini calls
7. **No training signal** — cache JSON is inference output, not ground truth
8. **Monolithic 1,300+ line script** — hard to test or swap models
9. **Filename-dependent validation** — `3_BHK.jpg` drives completeness expectations

### 4.6 Strengths (V3)

1. **Richest BIM output** in the workspace — Psets, quantities, materials, opening relations
2. **Deterministic IFC compiler** once JSON exists — model-agnostic downstream
3. **Robust property normalization** — handles Gemini schema drift
4. **Completeness guardrails** reduce obviously empty extractions
5. **`ifc_properties.py`** is a reusable BIM semantics encyclopedia
6. **Cache format** is a stable interchange artifact for experiments

### 4.7 Weaknesses (V3)

1. **Hallucination-prone coordinates** — no image-pixel grounding
2. **No topological model** — gaps/overlaps in wall networks
3. **Rooms never compiled** despite schema readiness
4. **Interior-wall collision fix is cosmetic** — shrinks visual box only
5. **Single-storey only**
6. **No confidence scores** on extractions
7. **Tight Gemini coupling** — `response_schema=BuildingAnalysis` is Google-specific

### 4.8 Reusable Components (Highest Priority for IMPROVED_MODEL_1)

| Priority | Component | Source |
|----------|-----------|--------|
| **P0** | `BuildingAnalysis` Pydantic models | `automated_bim_v4_connected.py` L58–110 |
| **P0** | `ifc_properties.py` | Full module — Psets, type maps, materials |
| **P0** | `build_detailed_ifc()` | JSON → IFC compiler |
| **P0** | Unit conversion helpers | `_to_meters`, `_normalize_point`, `_make_ifc_value` |
| **P1** | Type resolution | `resolve_component_spec`, `resolve_opening_spec`, maps |
| **P1** | Visual styling | `assign_material`, `assign_surface_style` |
| **P1** | Cache JSON workflow | Decouples perception from compilation |
| **P2** | ArchiCAD Pset extensions | Optional compatibility layer |
| **P2** | CLI patterns | `--force`, `--debug`, `--allow-low-detail` |

### 4.9 Components to Replace

| Current V3 Code | Vision Pipeline Replacement |
|-----------------|----------------------------|
| `analyze_floor_plan_detailed()` | Multi-model detection inference |
| `_build_extraction_prompt()`, retry logic | Topology validation + confidence thresholds |
| `_infer_bhk_count()`, count heuristics | Room detection from graph cycles |
| Gemini `response_schema` | `graph_builder` → `BuildingAnalysis` adapter |
| LLM-inferred centerlines | Line/segment detection + snap/merge |
| LLM `parent_wall_id` | Graph edge: opening → nearest wall by proximity + normal |
| LLM furniture placement | Icon detection + metric scale from annotations |

---

## 5. Cross-Version Comparison

### 5.1 Feature Matrix

| Feature | web_file | V1 | V2 | V3 |
|---------|----------|----|----|-----|
| **Paradigm** | YOLO-seg training | LLM→IFC | LLM→IFC | LLM→IFC |
| **Perception** | YOLO (stubbed labeler) | Gemini 3 Flash | Gemini 2.5 Flash | Gemini 2.5 Flash + retry |
| **Output contract** | YOLO polygons | BuildingAnalysis | BuildingAnalysis | BuildingAnalysis (rich) |
| **IFC generation** | None | Inline basic | Modular + Psets | Modular + voids + materials |
| **Units** | N/A | Pixels (broken) | Metres | Metres |
| **Rooms in IFC** | Room class for training | No | No | No |
| **Opening voids** | N/A | No | No | Partial (no boolean cut) |
| **Training UI** | Full web app | No | No | No |
| **Tests / CI** | No | No | No | No |
| **Lines of code** | ~4,400 | ~184 | ~1,082 | ~2,005 |

### 5.2 Evolution Diagram

```mermaid
flowchart TB
    subgraph training [Training Track - web_file]
        IMG_T[Floor Plan Images]
        MOCK[Mock Detector - BROKEN]
        YOLO[YOLOv8n-seg Labels]
        TRAIN[Ultralytics Train]
        CKPT[best_gdrive.pt]
        IMG_T --> MOCK --> YOLO --> TRAIN --> CKPT
    end

    subgraph v1 [V1 floorplan_ifc_ai]
        IMG1[Image] --> G1[Gemini 3 Flash]
        G1 --> J1[BuildingAnalysis]
        J1 --> IFC1[Basic IFC4]
    end

    subgraph v2 [V2 latest_interior]
        IMG2[Image] --> G2[Gemini 2.5 Flash]
        G2 --> J2[BuildingAnalysis + units]
        J2 --> IFC2[IFC4 + Psets]
    end

    subgraph v3 [V3 latest_interior_v1]
        IMG3[Image] --> G3[Gemini 2.5 + retry]
        G3 --> J3[Rich BuildingAnalysis]
        J3 --> IFC3[IFC4 + voids + materials]
    end

    subgraph target [IMPROVED_MODEL_1 Target]
        IMG4[Image] --> PRE[Preprocessing]
        PRE --> DET[Vision Detection]
        DET --> GR[Building Graph]
        GR --> TOP[Topology Validation]
        TOP --> J4[BuildingAnalysis]
        J4 --> IFC4[Reuse V3 IFC Compiler]
    end
```

### 5.3 The Integration Gap

The two tracks were **never connected**:

- `web_file` trains on **pixel-space polygon masks** (17 classes)
- IFC pipelines consume **metre-space centerline JSON** (`BuildingAnalysis`)

There is no converter from YOLO detections → `BuildingAnalysis`, no shared scale calibration, and no graph topology layer in either track.

**IMPROVED_MODEL_1 must bridge this gap.**

---

## 6. Reusable Components — Consolidated Inventory

### 6.1 Adopt Directly (P0)

| Component | Source | Role in New Architecture |
|-----------|--------|---------------------------|
| `BuildingAnalysis` schema | V3 `automated_bim_v4_connected.py` | **Target output of graph builder** |
| `ifc_properties.py` | V3 | **BIM semantics + IFC mapping** |
| `build_detailed_ifc()` | V3 | **Downstream IFC generator** (reference, not rewrite) |
| Unit helpers | V3 | **Pixel/graph → metre conversion** |
| 17-class taxonomy | `web_file/config/classes.py` | **Detection training labels** |
| YOLO-seg I/O | `web_file/web/auto_label.py` | **Intermediate mask format** |
| Dataset folder layout | `web_file` | **Training data organization** |
| Fine-tune config | `web_file` | **Small-dataset training reference** |

### 6.2 Adapt / Refactor (P1)

| Component | Adaptation |
|-----------|------------|
| `COMPONENT_TYPE_MAP` / `OPENING_TYPE_MAP` | Move to `bim_schema/` |
| Label correction UX | New annotation tool for masks + graph edges |
| Metadata sidecars | Add scale, graph version, annotation provenance |
| CubiCasa SVG parser (new) | Pseudo-ground-truth generator from `model_2.svg` |
| Cache JSON format | Versioned `BuildingAnalysis` with `schema_version` field |

### 6.3 Replace Entirely (P0)

| Component | Replacement |
|-----------|-------------|
| Gemini extraction (all versions) | Trainable vision models |
| Mock detector/analyzer/OCR | Real preprocessing + detection stack |
| LLM completeness heuristics | Geometric topology validation |
| LLM-inferred `parent_wall_id` | Graph-based opening-to-wall assignment |
| Monolithic scripts | Modular packages per layer |
| Train=val split | Proper data splits + evaluation harness |

---

## 7. Components to Replace — Rationale

### 7.1 Why Replace LLM Perception?

| LLM Failure Mode | Vision Model Advantage |
|------------------|------------------------|
| Hallucinated wall segments | Learned from labeled wall masks/lines |
| Invented metre coordinates | Pixel detections → calibrated scale → metres |
| Inconsistent `parent_wall_id` | Deterministic proximity + normal assignment |
| Token truncation on large plans | Tiled inference, no output length limit |
| Non-reproducible extractions | Same weights → same output |
| API cost per image | Amortized inference cost after training |
| No improvement loop | Fine-tune on corrections |

### 7.2 Why Not Replace IFC Compiler (Yet)?

V3's `build_detailed_ifc()` + `ifc_properties.py` are **deterministic, tested-by-use, and rich**. Rewriting them would delay the training architecture without reducing hallucination (the problem is upstream). The new pipeline should **feed the same JSON contract**.

### 7.3 Why Replace web_file Mock Pipeline?

The training UI and YOLO orchestration are valuable, but the **labeling pipeline is non-functional**. Restoring old heuristics would not outperform a modern detection architecture. The 17-class taxonomy and YOLO-seg format remain valid **intermediate representations** for walls, rooms, doors, windows, and furniture.

---

## 8. Technical Decisions for IMPROVED_MODEL_1

### 8.1 Schema as Contract

**Decision:** Use V3 `BuildingAnalysis` as the canonical BIM JSON schema, extended with optional fields:

```python
# Future extensions (not in V3 today)
class RoomData(BaseModel):
    room_id: str
    label: Optional[str]
    polygon: List[List[float]]  # metre-space boundary
    unit: str = "m"

class BuildingAnalysis(BaseModel):
    # ... existing fields ...
    rooms: List[RoomData] = []          # NEW — enables IfcSpace
    schema_version: str = "1.0"         # NEW — migration safety
    scale: Optional[ScaleMetadata] = None  # NEW — pixel→metre provenance
```

**Rationale:** V3 IFC compiler already understands walls/openings/interiors. Adding `rooms` unlocks `IfcSpace` defined in `ifc_properties.py` but never used.

### 8.2 Dual Representation During Training

**Decision:** Maintain both representations during training:

| Representation | Purpose |
|----------------|---------|
| YOLO-seg masks (pixel space) | Model training labels |
| `BuildingAnalysis` JSON (metre space) | BIM output + IFC compilation |

A `graph_builder` module converts detections + scale → `BuildingAnalysis`.

**Rationale:** Segmentation models train naturally on masks; BIM tools require metric centerlines.

### 8.3 Do Not Rewrite IFC Generator

**Decision:** Reference V3 compiler from `IMPROVED_MODEL_1/experiments/` via import or copied interface, not a fork.

**Rationale:** User constraint — focus on training architecture, not IFC generation.

### 8.4 Pseudo-Labels from SVG

**Decision:** Build a CubiCasa SVG parser as a **bootstrap labeling tool** using `model_2.svg`.

**Rationale:** Structured vector data provides free ground truth for walls, rooms, doors, windows — avoids cold-start LLM labeling.

---

## 9. Risks and Assumptions

### 9.1 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Training images not in repo | High | Download from [Era GDrive folder](https://drive.google.com/drive/folders/17PW8x6zq37e0ize5PVLV4h9EPKWUjMxZ); fix `dataset.yaml` paths |
| Class taxonomy mismatch (17 YOLO vs 3 BIM categories) | Medium | Define explicit mapping layer in `bim_schema/` |
| Wall as instance seg vs centerline | High | Two-stage: wall mask → skeletonize → graph, or dedicated line detection head |
| Scale unknown in raster plans | High | OCR dimension lines + door-width prior (0.9 m) |
| V3 JSON used as training GT | High | Treat cache JSON as **weak pseudo-labels only** |
| No evaluation harness | Medium | Build geometry metrics (wall IoU, opening recall) in `experiments/` |

### 9.2 Assumptions

1. The [Era dataset](https://drive.google.com/drive/folders/17PW8x6zq37e0ize5PVLV4h9EPKWUjMxZ) floor plan images are representative of production inputs.
2. YOLOv8-seg (or successor) remains a viable baseline for instance segmentation.
3. V3 `BuildingAnalysis` schema is sufficient for initial IFC output; rooms can be added incrementally.
4. Existing IFC compilers remain reference-only; `IMPROVED_MODEL_1` will not modify them.
5. Gemini extractions in `*_Detailed_Cache.json` files are useful for **comparison baselines**, not supervised labels.

---

## 10. Recommended Next Steps (Phases 2–5 Preview)

| Phase | Deliverable | Depends On |
|-------|-------------|------------|
| **2** | `DATASET_ANALYSIS.md` | Floor plan image inspection (GDrive / local) |
| **3** | `SYSTEM_DESIGN.md` | Phases 1–2 |
| **4** | `IMPROVED_MODEL_1/` package skeleton | Phase 3 |
| **5** | `IMPLEMENTATION_ROADMAP.md` | Phase 3 |

---

## Appendix A — Key File Paths

| Purpose | Path |
|---------|------|
| Training class taxonomy | `D:\HCI_interor\web_file\config\classes.py` |
| Training server | `D:\HCI_interor\web_file\web\server.py` |
| YOLO label I/O | `D:\HCI_interor\web_file\web\auto_label.py` |
| Mock detector | `D:\HCI_interor\web_file\logic\detector.py` |
| V1 monolith | `D:\HCI_interor\floorplan_ifc_ai\main.py` |
| V2 compiler | `D:\HCI_interor\latest_interior\latest_interior\automated_bim_v4_connected.py` |
| V2 properties | `D:\HCI_interor\latest_interior\latest_interior\ifc_properties.py` |
| V3 compiler | `D:\HCI_interor\latest_interior_v1\latest_interior_v1\automated_bim_v4_connected.py` |
| V3 properties | `D:\HCI_interor\latest_interior_v1\latest_interior_v1\ifc_properties.py` |
| V3 example cache | `D:\HCI_interor\latest_interior_v1\latest_interior_v1\model_2_Detailed_Cache.json` |
| CubiCasa SVG test asset | `D:\HCI_interor\latest_interior\latest_interior\model_2.svg` |
| Dataset stub | `D:\HCI_interor\gdrive_dataset\dataset.yaml` |

---

## Appendix B — Glossary

| Term | Definition |
|------|------------|
| **BuildingAnalysis** | Pydantic root model: walls, openings, interiors in metre space |
| **Centerline wall** | Wall represented as a line segment (start_pt → end_pt) with thickness |
| **YOLO-seg** | YOLO instance segmentation format: class + normalized polygon |
| **BHK** | Bedroom-Hall-Kitchen count (e.g., 3 BHK = 3 bedrooms) |
| **Pset** | IFC Property Set (e.g., `Pset_WallCommon`) |
| **Pseudo-label** | Machine-generated label used for training, not human-verified ground truth |

---

*End of Phase 1 — Architecture Analysis*
