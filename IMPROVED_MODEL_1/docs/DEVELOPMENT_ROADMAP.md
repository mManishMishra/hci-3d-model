# Development Roadmap

**Project:** IMPROVED_MODEL_1  
**Horizon:** 4 weeks (foundation phase — no production training at scale yet)  
**Date:** 2026-06-09

---

## Roadmap Summary

| Week | Theme | Primary Deliverable |
|------|-------|-------------------|
| **Week 1** | Foundation + Preprocessing + Detection scaffold | Runnable preprocess → detect on `model_2.svg` |
| **Week 2** | Graph + Topology + BIM schema | Valid `building.json` from CubiCasa SVG |
| **Week 3** | IFC adapter + Pipeline + Dataset ingest | End-to-end IFC from vision pipeline |
| **Week 4** | Training infra + Viewer + Evaluation | First YOLO training run + metrics dashboard |

---

## Week 1 — Foundation, Preprocessing, Detection Scaffold

### Goals
- Project skeleton with configs, deps, and test harness
- Image preprocessing pipeline operational
- CubiCasa SVG parser producing pseudo-detections
- YOLO detector wrapper (inference-ready, untrained or COCO-pretrained)

### Deliverables

| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| W1-D1 | `pyproject.toml`, `requirements.txt`, `.gitignore` | `pip install -e .` succeeds |
| W1-D2 | `configs/*.yaml` skeleton | All layers configurable |
| W1-D3 | `preprocessing/image_loader.py`, `enhance.py` | Loads JPG/PNG/SVG; outputs 1280px long-edge |
| W1-D4 | `preprocessing/svg_parser.py` | Parses `model_2.svg` → spaces, walls, doors, windows |
| W1-D5 | `training/pseudo_labeler.py` | SVG → YOLO-seg label files for CubiCasa sample |
| W1-D6 | `detection/yolo_detector.py` | Runs `yolov8n-seg.pt` inference; returns `DetectionResult` |
| W1-D7 | `detection/postprocess.py` | Mask → polygon; wall skeletonization prototype |
| W1-D8 | `tests/unit/test_preprocess.py` | CI-green on fixtures |
| W1-D9 | `scripts/pseudo_label_svg.py` | CLI: SVG in → labels out |

### Tasks

1. Create folder structure per `FOLDER_STRUCTURE.md`
2. Pin dependencies per `TECH_STACK.md`
3. Copy class taxonomy to `configs/classes.yaml` from `web_file/config/classes.py`
4. Implement SVG parser against `model_2.svg` structure
5. Generate first pseudo-labels in `dataset/labels/train/`
6. Wire YOLO detector with class-agnostic COCO weights (smoke test only)
7. Document preprocess API in module docstrings

### Risks
- SVG parser complexity — **mitigate:** scope to CubiCasa v1.1 only for Week 1
- No GPU — **mitigate:** nano model on CPU acceptable for dev

### Do NOT
- Start full dataset download training
- Modify any legacy project files

---

## Week 2 — Building Graph, Topology, BIM Schema

### Goals
- Convert detections (or SVG ground truth) into `BuildingGraph`
- Scale calibration from SVG dimension labels
- Topology validator enforcing architectural rules
- `BuildingAnalysis` JSON emission

### Deliverables

| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| W2-D1 | `graph_builder/types.py` | Pydantic models for graph |
| W2-D2 | `graph_builder/wall_graph.py` | ≥90% corners snapped on `model_2` |
| W2-D3 | `graph_builder/opening_assigner.py` | All doors/windows attached to walls |
| W2-D4 | `graph_builder/room_extractor.py` | Room polygons match SVG spaces |
| W2-D5 | `graph_builder/scale_calibrator.py` | metre coordinates within 5% of SVG labels |
| W2-D6 | `topology/validator.py` | Passes on clean CubiCasa graph |
| W2-D7 | `topology/repair.py` | Auto-fixes snap warnings |
| W2-D8 | `bim_schema/models.py` | V3-compatible + `rooms`, `schema_version` |
| W2-D9 | `bim_schema/adapter.py` | `graph.json` → `building.json` |
| W2-D10 | `tests/integration/test_pipeline_cubicasa.py` | Graph + BIM golden file match |

### Tasks

1. Implement wall centerline extraction from SVG wall polygons (bypass YOLO for GT path)
2. Build corner snap + collinear merge with configurable ε
3. Implement opening-to-wall projection algorithm
4. Extract room faces from space polygons
5. Parse SVG `DimensionMeasureLabel` for scale validation
6. Port type maps from V3 `ifc_properties.py` into `bim_schema/type_maps.py`
7. Write 8+ topology rules from LLD
8. Generate golden `tests/fixtures/golden_building.json`

### Risks
- Wall polygon → centerline ambiguity — **mitigate:** use CubiCasa wall midlines where available
- Graph face extraction edge cases — **mitigate:** prefer room masks over pure graph cycles for Phase 1

### Milestone M2 + M3
- Valid `BuildingAnalysis` JSON from `model_2.svg` without Gemini

---

## Week 3 — IFC Adapter, Pipeline Orchestration, Dataset Ingest

### Goals
- V3 IFC compiler adapter producing valid `.ifc`
- Full `PipelineRunner` chaining all stages
- Dataset ingestion from GDrive
- Baseline comparison script (vision vs Gemini cache)

### Deliverables

| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| W3-D1 | `ifc_generator/v3_adapter.py` | Compiles `building.json` → `model.ifc` |
| W3-D2 | `ifc_generator/compile.py` | Public `compile_ifc()` API |
| W3-D3 | `pipeline/runner.py` | Single command: image → IFC |
| W3-D4 | `pipeline/artifacts.py` | All stage artifacts persisted |
| W3-D5 | `scripts/run_pipeline.py` | CLI with `--stage`, `--force` flags |
| W3-D6 | `training/dataset_manager.py` | GDrive ingest → `dataset/raw/` |
| W3-D7 | `scripts/ingest_dataset.py` | Downloads Era or training folder |
| W3-D8 | `scripts/compare_gemini.py` | Wall count/length diff vs V3 cache |
| W3-D9 | `tests/integration/test_ifc_compile.py` | IFC opens without schema errors |
| W3-D10 | `docs/DATASET_ANALYSIS.md` | Floor plan image characteristics |

### Tasks

1. Implement read-only V3 import via `configs/paths.yaml`
2. Wire `graph_to_building_analysis` → `build_detailed_ifc`
3. Add pipeline fail-on-validation-error behavior
4. Resolve GDrive folder ID (align code `18IT...` vs Era `17PW...` with team)
5. Download sample batch (50–100 images) for labeling prep
6. Run Gemini baseline on 3–5 images for comparison metrics
7. Set up MLflow tracking URI in `experiments/`

### Risks
- V3 import path issues on Windows — **mitigate:** absolute paths in `paths.yaml`
- GDrive quota/auth — **mitigate:** manual download fallback documented

### Milestone M4
- End-to-end: `model_2.svg` → IFC viewable in viewer

---

## Week 4 — Training Infrastructure, Viewer, Evaluation

### Goals
- First real YOLO training run on pseudo + downloaded labels
- 3D IFC viewer operational
- Evaluation metrics vs CubiCasa ground truth
- Documentation complete for handoff to scale-up training

### Deliverables

| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| W4-D1 | `training/trainer.py` | Trains on `dataset/labels/` with val split |
| W4-D2 | `training/evaluator.py` | Reports mask IoU per class |
| W4-D3 | `scripts/train.py` | CLI training entry point |
| W4-D4 | `scripts/evaluate.py` | Post-train evaluation report |
| W4-D5 | `viewer/static/` IFC.js viewer | Loads `model.ifc` in browser |
| W4-D6 | `viewer/overlay_viewer.py` | 2D detection overlay JPEG |
| W4-D7 | `training/evaluator.py` wall endpoint metric | Reported on `model_2` holdout |
| W4-D8 | MLflow experiment dashboard | All runs logged |
| W4-D9 | README.md quickstart | New developer can run pipeline in <30 min |
| W4-D10 | Phase 2 roadmap draft | Multimodal + interior extensions |

### Tasks

1. Generate pseudo-labels for all available SVGs (if any beyond `model_2`)
2. Manually correct 10–20 raster plans in CVAT (if downloaded)
3. Train `yolov8n-seg` for 50 epochs on available labels
4. Integrate trained weights into `detection/yolo_detector.py`
5. Re-run full pipeline on 5 held-out images
6. Build static IFC viewer page
7. Produce evaluation report: vision vs Gemini baseline
8. Review topology pass rate across batch

### Risks
- Insufficient labeled data — **mitigate:** pseudo-labels + heavy augment
- Low wall IoU on raster — **mitigate:** document as Phase 2 training priority

### Milestone M5
- First trained checkpoint integrated into inference pipeline

---

## Post–Week 4 Backlog (Phase 2 Preview)

| Priority | Item | Est. |
|----------|------|------|
| P0 | OCR scale calibration for raster plans | 1 week |
| P0 | `IfcSpace` compilation from `rooms[]` | 1 week |
| P0 | CVAT annotation workflow + 200+ labeled plans | 2–3 weeks |
| P1 | YOLO medium model + class-weighted loss | 1 week |
| P1 | Boolean wall cuts for openings | 1 week |
| P1 | Active learning loop (low-conf → annotate) | 2 weeks |
| P2 | ONNX export + batch inference | 1 week |
| P2 | FastAPI deployment wrapper | 1 week |
| P2 | Multimodal GNN graph refiner | 3–4 weeks |
| P3 | Interior layout generation module | 4+ weeks |

---

## Team Roles (Suggested)

| Role | Week 1–2 | Week 3–4 |
|------|----------|----------|
| ML Engineer | Detection + training | Training + evaluation |
| CV/Geometry Engineer | Graph + topology | Scale + OCR |
| BIM Engineer | Schema + IFC adapter | Viewer + IfcSpace |
| Data Engineer | SVG parser + ingest | GDrive + CVAT pipeline |

---

## Definition of Done — Foundation Phase

- [ ] All folders in `FOLDER_STRUCTURE.md` exist with module stubs
- [ ] `scripts/run_pipeline.py --image model_2.svg` produces `model.ifc`
- [ ] Topology validator blocks intentionally broken graphs
- [ ] No files modified outside `IMPROVED_MODEL_1/`
- [ ] `pytest` passes unit + integration tests
- [ ] MLflow logs at least one training run
- [ ] IFC viewer renders output in browser
- [ ] Evaluation report compares vision vs Gemini on ≥3 plans
- [ ] All docs in `docs/` index complete

---

## Weekly Checkpoint Meetings

| Week | Demo |
|------|------|
| 1 | SVG → pseudo-labels + preprocess output |
| 2 | `building.json` + validation report |
| 3 | Full pipeline → IFC file |
| 4 | Trained model inference + viewer + metrics |

---

*End of Development Roadmap*
