# Technical Audit Report

**Project:** IMPROVED_MODEL_1  
**Role:** Lead AI Architect Audit  
**Date:** 2026-06-09  
**Scope:** `floorplan_ifc_ai`, `latest_interior`, `latest_interior_v1`, `web_file`, `gdrive_dataset`

---

## 1. Executive Summary

The HCI Interior workspace contains **two disconnected engineering tracks**:

1. **IFC Generation (V1→V3):** Mature LLM→JSON→IFC pipeline with rich BIM metadata. Perception is 100% Gemini-dependent. Downstream IFC compilation is the strongest asset.
2. **Training (web_file):** Complete YOLOv8-seg training UI and orchestration. **Labeling pipeline is non-functional** (mock detectors). Dataset directory is an empty stub.

**Production readiness:** Neither track can serve as a production AI training pipeline today. V3 can produce IFC files from cached Gemini JSON but cannot learn, improve, or guarantee geometric accuracy. `web_file` cannot generate training labels.

**Strategic direction:** Build `IMPROVED_MODEL_1` as a **unified vision-first pipeline** that produces V3-compatible `BuildingAnalysis` JSON from deterministic detections and graph topology, then compiles to IFC via IfcOpenShell.

---

## 2. Existing Architecture

### 2.1 Workspace Topology

```
D:\HCI_interor\
├── floorplan_ifc_ai/          V1 — 1-file LLM→IFC prototype (~184 LOC)
├── latest_interior/           V2 — 2-file property-rich compiler (~1,082 LOC)
├── latest_interior_v1/          V3 — advanced LLM→IFC (~2,005 LOC)
├── web_file/                  Training web app (~4,400 LOC, 8 files)
├── gdrive_dataset/            Dataset stub (dataset.yaml only)
└── IMPROVED_MODEL_1/          New project (design only)
```

### 2.2 Architectural Pattern — IFC Track

All three IFC versions share the same conceptual architecture:

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────┐
│ Floor Plan  │───▶│ Gemini Vision API │───▶│ BuildingAnalysis │───▶│ IFC4     │
│ Image       │    │ (structured JSON) │    │ (Pydantic/JSON)  │    │ (.ifc)   │
└─────────────┘    └──────────────────┘    └─────────────────┘    └──────────┘
                              │                      │
                              ▼                      ▼
                     *_Detailed_Cache.json    ifc_properties.py
```

**V1** embeds extraction + compilation in `main.py`.  
**V2** splits `ifc_properties.py` for BIM semantics.  
**V3** adds extraction guardrails, materials, opening void relations, typed components.

### 2.3 Architectural Pattern — Training Track

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐    ┌──────────────┐
│ images_raw/ │───▶│ Auto-label        │───▶│ labels/     │───▶│ YOLOv8-seg   │
│ (GDrive)    │    │ (detector+OCR)    │    │ train/*.txt │    │ train        │
└─────────────┘    └──────────────────┘    └─────────────┘    └──────────────┘
                              │                                        │
                              ▼                                        ▼
                     marked/*_labelled.jpg                    best_gdrive.pt
```

**Critical failure:** Auto-label depends on `FloorPlanDetector.detect()` which returns **empty lists for all classes**. Pipeline stops at SKIP for every image.

### 2.4 Integration Gap

| Dimension | Training track | IFC track |
|-----------|---------------|-----------|
| Coordinate space | Pixel-normalized [0,1] polygons | Metre-space centerlines |
| Output schema | YOLO-seg lines | `BuildingAnalysis` JSON |
| Element model | 17 instance classes | Walls, openings, interiors |
| Rooms | Class ID 3 (Room mask) | Not compiled to `IfcSpace` |
| Scale | None | Assumed metres (V2/V3) |
| Converter | **Does not exist** | N/A |

No module bridges YOLO detections → `BuildingAnalysis`. This is the primary integration debt.

---

## 3. Existing IFC Generation Workflow

### 3.1 Version Comparison

| Stage | V1 (`floorplan_ifc_ai`) | V2 (`latest_interior`) | V3 (`latest_interior_v1`) |
|-------|-------------------------|------------------------|---------------------------|
| **Entry** | `main.py` CLI | `automated_bim_v4_connected.py` | Same + `run.sh` |
| **Model** | `gemini-3-flash-preview` | `gemini-2.5-flash` | `gemini-2.5-flash` |
| **Temperature** | 0.1 | 0.1 | 0.0 |
| **Retry** | None | None | BHK-aware completeness retry |
| **Units** | None (pixels) | `_to_meters()` | `_to_meters()` + aliases |
| **Wall IFC** | `IfcWall`, 3m fixed | `IfcWallStandardCase` | `IfcWallStandardCase` + collision polys |
| **Openings** | Orphan placement | Orphan + Psets | `IfcOpeningElement` void/fill |
| **Interiors** | Corner boxes | Corner boxes + Psets | Center boxes + materials |
| **Rooms** | No | No (schema exists) | No (schema exists) |
| **Properties** | None | Full `IFC_SCHEMA` | + type maps, material colors |
| **Cache** | Optional skip | Optional skip | Auto-named + `--force` |

### 3.2 V3 Detailed Workflow

```
1. CLI parse args (--image, --output, --cache, --force, --debug, --allow-low-detail)
2. If cache exists and not --force → load JSON
3. Else:
   a. Read image bytes, detect MIME
   b. Build prompt (_build_extraction_prompt + BHK hints)
   c. Gemini generate_content(response_schema=BuildingAnalysis)
   d. If suspicious counts → retry with repair prompt
   e. If still suspicious → exit (unless --allow-low-detail)
   f. Write cache JSON
4. Load ifc_properties.py via importlib walk
5. build_detailed_ifc():
   a. IFC4 project shell (Project→Site→Building→Storey)
   b. For each wall: centerline extrusion + Psets + quantities
   c. For each opening: void element + door/window fill + Psets
   d. For each interior: typed entity + material + surface style
   e. IfcRelContainedInSpatialStructure
6. model.write(output.ifc)
```

### 3.3 JSON Contract (`BuildingAnalysis`)

Root schema from V3 (`automated_bim_v4_connected.py`):

- `building_name: str`
- `walls: List[WallData]` — centerline segments with thickness, height, unit
- `openings: List[OpeningComponent]` — doors/windows with `parent_wall_id`
- `interiors: List[InteriorComponent]` — furniture/sanitary/appliance with type, material, color

**Not in schema today:** `rooms`, `scale`, `schema_version`, `confidence` fields.

### 3.4 IFC Output Quality Assessment

| Capability | V1 | V2 | V3 |
|------------|----|----|-----|
| Valid IFC4 syntax | Yes | Yes | Yes |
| Physically correct scale | No | Depends on Gemini | Depends on Gemini |
| Opening wall cuts (boolean) | No | No | Partial (relations only) |
| IfcSpace rooms | No | No | No |
| IfcSlab floors | No | No | No |
| ArchiCAD Psets | No | Yes | Yes |
| Material visualization | No | No | Yes |
| Multi-storey | No | No | No |

---

## 4. Existing Training Workflow

### 4.1 `web_file` Pipeline

**Server:** FastAPI (`web/server.py`, port 3000)  
**Frontend:** Single-page app (`web/index.html`) with Train / Correct / Test tabs

| Step | Endpoint / Module | Status |
|------|-------------------|--------|
| Download dataset | `POST /api/download` (gdown) | Works if GDrive accessible |
| Upload images | `POST /api/upload` | Works |
| Auto-label | `POST /api/autolabel` → `_autolabel_worker` | **Broken** (mock detector) |
| Train | `POST /api/train` → Ultralytics | Works **if labels exist** |
| Fine-tune | `POST /api/train_from_corrections` | Works if labels exist |
| Inference | `POST /api/detect` | Works if model exists |
| Correct labels | `/api/correct`, `/api/section`, `/api/resize_label` | Works on loaded labels |
| Stream progress | `GET /api/stream` (SSE) | Works |

### 4.2 Expected Dataset Layout

```
gdrive_dataset/
├── dataset.yaml
├── images_raw/
├── images/train/
├── labels/train/*.txt
├── marked/
├── metadata/
└── runs/train/weights/best.pt
```

### 4.3 Label Format

YOLO instance segmentation — one polygon per line:

```
<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>
```

17 classes defined in `web_file/config/classes.py` (Wall=0 through EnergyConversionDevice=16).

### 4.4 Training Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| Base model | `yolov8n-seg.pt` | Nano segmentation |
| Epochs | 50 | UI configurable |
| Batch | 4 | UI configurable |
| Image size | 640 | UI configurable |
| Device | CUDA → MPS → CPU | Auto-detect |
| Fine-tune LR | 0.0005 | SGD, freeze=10 layers |
| Val split | **Same as train** | Design flaw |

### 4.5 `gdrive_dataset` Audit

| Item | Expected | Actual |
|------|----------|--------|
| `dataset.yaml` | Yes | Yes (stub, wrong `path`) |
| Images | Hundreds+ | **0** |
| Labels | Per image | **0** |
| Metadata | Per image | **0** |
| Training runs | After train | **0** |
| `best_gdrive.pt` | Active model | **Missing** |
| `yolov8n-seg.pt` | Base weights | **Missing** |

**GDrive folder IDs (inconsistent):**
- Code (`web_file`): `18IThRKRGUHFXnSiMtJlhqHSphDIuphNk`
- Docs / Era dataset: `17PW8x6zq37e0ize5PVLV4h9EPKWUjMxZ`

**Only in-repo floor plan asset:** `latest_interior/latest_interior/model_2.svg` (CubiCasa, 1514×1312 SVG units) — not in `gdrive_dataset`.

---

## 5. Reusable Modules

### 5.1 High Priority — Adopt Directly

| Module | Source | Reuse Strategy |
|--------|--------|----------------|
| `BuildingAnalysis` Pydantic models | V3 `automated_bim_v4_connected.py` | **Canonical BIM JSON contract**; extend with `rooms`, `scale`, `schema_version` |
| `ifc_properties.py` | V3 | **Copy interface** into `bim_schema/`; reference semantics, do not fork logic unnecessarily |
| `build_detailed_ifc()` | V3 | **Adapter import** from `ifc_generator/` experiments; compile-only stage |
| Unit helpers | V3 (`_to_meters`, `_normalize_point`) | **Reuse** in graph→JSON adapter |
| Type resolution maps | V3 (`COMPONENT_TYPE_MAP`, `OPENING_TYPE_MAP`) | **Move** to `bim_schema/` |
| 17-class taxonomy | `web_file/config/classes.py` | **Detection training labels** |
| YOLO-seg I/O | `web_file/web/auto_label.py` | **Label read/write** utilities |
| Dataset folder convention | `web_file` | **Extend** with val/test splits |
| Fine-tune hyperparameters | `web_file` `_finetune_worker` | **Reference config** for small-dataset training |
| CubiCasa SVG structure | `model_2.svg` | **Bootstrap pseudo-label generator** (new parser) |
| Cache JSON pattern | V1–V3 `*_Detailed_Cache.json` | **Experiment artifacts** and baseline comparison |

### 5.2 Medium Priority — Adapt

| Module | Adaptation |
|--------|------------|
| Label correction UX (`index.html`) | Inspire new annotation tool; decouple from monolith |
| Metadata sidecars (`image_metadata.py`) | Extend with scale, graph version, annotation provenance |
| Training SSE progress pattern | Reuse in training job monitor |
| `normalize_opening_type()` | Post-detection symbol classifier output |
| ArchiCAD Pset helpers | Optional IFC extension layer |

### 5.3 Reference Only — Do Not Copy Blindly

| Module | Reason |
|--------|--------|
| V3 `analyze_floor_plan_detailed()` | LLM-specific; replace entirely |
| V3 completeness heuristics | Replace with geometric validation |
| `web_file` mock detectors | Replace with real CV stack |
| V1 wall compiler | Superseded by V3 |
| Bundled `floorplan_ifc_ai/venv` | Use fresh environment with pinned deps |

---

## 6. Non-Reusable Modules

| Module | Source | Why Not Reusable |
|--------|--------|------------------|
| Gemini extraction pipeline | V1–V3 | Target architecture removes LLM from perception |
| `_infer_bhk_count()` / retry prompts | V3 | Filename heuristics ≠ geometric validation |
| Mock `FloorPlanDetector` | `web_file` | Returns empty; no logic |
| Mock `floor_plan_analyzer` | `web_file` | Passthrough stub |
| Mock `room_text_mapper` | `web_file` | No OCR |
| Monolithic `server.py` | `web_file` | 1,510 lines; wrong separation of concerns |
| Inline SPA `index.html` | `web_file` | 2,900 lines; not modular |
| In-memory `_analysis` store | `web_file` | Not scalable |
| Model weight merge | `web_file` | Naive arithmetic; not production-safe |
| V1 opening compiler | V1 | Orphan doors; no hosting |
| V1 unit handling | V1 | Writes pixels as metres |
| Train=val=test split | `web_file` | Invalid evaluation |
| Hardcoded GDrive path in `dataset.yaml` | `gdrive_dataset` | Wrong machine path |

---

## 7. Technical Debt

### 7.1 Critical

| ID | Debt | Impact |
|----|------|--------|
| TD-01 | Mock CV modules in `web_file` | Training pipeline non-functional |
| TD-02 | No training images in repo | Cannot train or evaluate |
| TD-03 | LLM as sole perception (V1–V3) | Hallucination, non-reproducible geometry |
| TD-04 | No YOLO→BIM converter | Two tracks never integrated |
| TD-05 | `corrected_rooms` NameError bug | `web_file` autolabel crashes if detector ever works |

### 7.2 High

| ID | Debt | Impact |
|----|------|--------|
| TD-06 | No train/val/test split | Inflated metrics |
| TD-07 | No `requirements.txt` anywhere | Non-reproducible environments |
| TD-08 | Monolithic 1,300+ line IFC script | Untestable, hard to extend |
| TD-09 | `IfcSpace` schema unused | Rooms never in BIM output |
| TD-10 | Opening voids without boolean cut | Visually incorrect wall geometry |
| TD-11 | Two different GDrive folder IDs | Dataset source confusion |

### 7.3 Medium

| ID | Debt | Impact |
|----|------|--------|
| TD-12 | SVG rasterized only in preview, not autolabel | SVG inputs fail labeling |
| TD-13 | `metadata_choice` dead parameter | UI misleading |
| TD-14 | BBox corrections degrade to rectangles | Segmentation fidelity loss |
| TD-15 | IFC cache JSON treated as potential GT | Risk of training on hallucinations |
| TD-16 | No evaluation harness | Cannot measure improvement |
| TD-17 | No version field on cache JSON | Schema migration risk |
| TD-18 | Single-storey hardcoded | Multi-floor plans unsupported |

### 7.4 Low

| ID | Debt | Impact |
|----|------|--------|
| TD-19 | `sam_env/` path comments in `web_file` | Developer confusion |
| TD-20 | Revert API expects `.bak` never written | Data loss risk |
| TD-21 | `_training_lock` defined but unused | Potential race |
| TD-22 | Bundled venv in `floorplan_ifc_ai` | Large repo footprint |

---

## 8. Current Bottlenecks

### 8.1 Perception Bottlenecks

| Bottleneck | Location | Severity |
|------------|----------|----------|
| Single Gemini call for all geometry | V3 | Critical |
| 8192 output token limit | V3 | High on large plans |
| No pixel→metre calibration | V1–V3 | Critical |
| No confidence scores | V1–V3 | High |
| Filename-dependent validation | V3 | Medium |

### 8.2 Training Bottlenecks

| Bottleneck | Location | Severity |
|------------|----------|----------|
| Empty auto-label output | `web_file` | Critical |
| No labeled dataset | `gdrive_dataset` | Critical |
| Wall class never pseudo-labeled | `web_file` | High |
| No annotation tool for graph edges | N/A | High |
| No active learning loop | `web_file` | Medium |

### 8.3 BIM Compilation Bottlenecks

| Bottleneck | Location | Severity |
|------------|----------|----------|
| Sequential Python entity creation | V3 | Low at current scale |
| No room compilation | V3 | High for spatial program |
| No boolean wall cuts | V3 | Medium |
| Interior collision shrink is cosmetic | V3 | Medium |

### 8.4 Operational Bottlenecks

| Bottleneck | Impact |
|------------|--------|
| API cost per image (Gemini) | Blocks scale |
| No CI/CD or regression tests | Blocks safe iteration |
| No containerization | Blocks deployment |
| No experiment tracking | Blocks model comparison |

---

## 9. Missing Components for Production AI Training

### 9.1 Data Layer

| Component | Status | Required For |
|-----------|--------|--------------|
| Curated floor plan image dataset | Missing | Training |
| Human-verified labels (YOLO-seg) | Missing | Supervised learning |
| Train/val/test splits with stratification | Missing | Reliable metrics |
| Label versioning (DVC or similar) | Missing | Reproducibility |
| Pseudo-label pipeline (SVG→masks) | Missing | Cold start |
| Scale annotation metadata | Missing | Metre conversion |
| Data ingestion CLI | Partial (`web_file` GDrive) | Automation |

### 9.2 Model Layer

| Component | Status | Required For |
|-----------|--------|--------------|
| Working wall detector | Missing | Core perception |
| Door/window symbol detector | Missing | Opening extraction |
| Room segmentation model | Missing | Space graph |
| OCR for dimension text | Missing | Scale calibration |
| Model registry / versioning | Partial | Experiment management |
| Export to ONNX/TorchScript | Missing | Deployment |
| Multi-GPU training support | Missing | Scale |

### 9.3 Geometry Layer

| Component | Status | Required For |
|-----------|--------|--------------|
| Wall mask → centerline extractor | Missing | BIM graph |
| Corner snap / collinear merge | Missing | Clean topology |
| Opening-to-wall assignment | Missing | Valid BIM |
| Room cycle detection | Missing | IfcSpace |
| Scale estimator | Missing | Metre accuracy |
| Topology validation rules | Missing | Quality gate |

### 9.4 Pipeline Layer

| Component | Status | Required For |
|-----------|--------|--------------|
| Detection → BuildingAnalysis adapter | Missing | End-to-end |
| Config-driven pipeline runner | Missing | Experiments |
| Evaluation metrics (IoU, topology) | Missing | Model selection |
| Baseline comparison (Gemini vs vision) | Missing | ROI proof |
| Batch inference | Missing | Throughput |

### 9.5 Infrastructure Layer

| Component | Status | Required For |
|-----------|--------|--------------|
| `requirements.txt` / `pyproject.toml` | Missing | Reproducibility |
| Docker / devcontainer | Missing | Onboarding |
| CI (lint, test, smoke IFC) | Missing | Quality |
| Experiment tracking (MLflow/W&B) | Missing | Training ops |
| Annotation UI (or CVAT integration) | Partial (`web_file`) | Human-in-loop |

### 9.6 Viewer Layer

| Component | Status | Required For |
|-----------|--------|--------------|
| 3D BIM viewer | Missing | Validation UX |
| 2D overlay (detections on plan) | Partial (`web_file` marked images) | Debug |
| Side-by-side Gemini vs vision compare | Missing | Evaluation |

---

## 10. Audit Conclusions

### 10.1 What Works Today

- V3 produces the richest IFC output with property sets, materials, and opening relations
- `BuildingAnalysis` is a viable interchange contract between perception and compilation
- `web_file` demonstrates a complete human-in-the-loop training UX pattern
- CubiCasa SVG provides structured ground truth for bootstrap labeling
- YOLO-seg format and 17-class taxonomy are sound training targets

### 10.2 What Does Not Work Today

- End-to-end training (no labels, no working auto-labeler)
- Geometric accuracy (LLM hallucination in all IFC versions)
- Production deployment (no tests, no containers, no pinned deps)
- Room-aware BIM (schema exists, never compiled)
- Unified pipeline (training and IFC tracks are siloed)

### 10.3 Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Era dataset style mismatch | Medium | High | Dataset analysis before model design |
| Wall centerline from masks is hard | High | High | Dual-head: seg + line detection |
| Scale unknown in raster plans | High | High | OCR + door-width prior |
| V3 JSON used as training GT | Medium | Critical | Explicit pseudo-label tiering |
| Scope creep into IFC rewrite | Medium | Medium | Adapter pattern; freeze compiler interface |

---

*End of Technical Audit Report*
