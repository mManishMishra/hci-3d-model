# Folder Structure

**Project:** IMPROVED_MODEL_1  
**Root:** `D:\HCI_interor\IMPROVED_MODEL_1`  
**Version:** 1.0  
**Date:** 2026-06-09

---

## 1. Design Goals

- **One module per pipeline layer** — matches HLD/LLD boundaries
- **Configs separate from code** — reproducible experiments
- **Artifacts outside git** — large binaries in `data/` and `experiments/` (gitignored)
- **Docs co-located** — all design artifacts in `docs/`
- **No modification** of sibling projects — reference via adapter paths in config only

---

## 2. Complete Directory Tree

```
IMPROVED_MODEL_1/
│
├── README.md                          # Project overview + quickstart (post-implementation)
├── pyproject.toml                     # Package metadata + tool config (Phase 1 setup)
├── requirements.txt                   # Pinned runtime dependencies
├── requirements-dev.txt               # pytest, ruff, mlflow
├── requirements-gpu.txt               # CUDA torch variants
├── .gitignore                         # data/, experiments/, *.pt, venv/
├── .env.example                       # GEMINI_API_KEY (baseline only), MLFLOW_URI
│
├── configs/                           # All YAML configuration
│   ├── pipeline.yaml                  # Master pipeline config
│   ├── preprocess.yaml                # Preprocessing parameters
│   ├── detection.yaml                 # YOLO model paths, thresholds
│   ├── graph.yaml                     # Snap tolerances, default wall height
│   ├── topology.yaml                  # Validation rules + thresholds
│   ├── classes.yaml                   # 17-class taxonomy (from web_file)
│   ├── dataset.yaml                   # Generated — do not hand-edit
│   ├── training.yaml                  # Epochs, batch, augmentations
│   └── paths.yaml                     # Legacy project reference paths (read-only)
│
├── preprocessing/                     # Layer 1: Image preprocessing
│   ├── __init__.py
│   ├── image_loader.py                # Format detection, load, SVG rasterize
│   ├── enhance.py                     # Deskew, resize, binarize
│   ├── svg_parser.py                  # CubiCasa SVG → structured model
│   └── caption_removal.py             # Optional title block removal (Phase 2)
│
├── detection/                         # Layer 2: YOLO + OCR detection
│   ├── __init__.py
│   ├── yolo_detector.py               # Ultralytics wrapper
│   ├── postprocess.py                 # NMS, mask→polygon, wall centerlines
│   ├── ocr_module.py                  # Dimension + room label OCR (Phase 2)
│   └── models/                        # .gitignore — downloaded weights
│       └── .gitkeep
│
├── graph_builder/                     # Layer 3: Building graph
│   ├── __init__.py
│   ├── wall_graph.py                  # Wall segment graph construction
│   ├── opening_assigner.py            # Door/window → wall edge
│   ├── room_extractor.py              # Room polygons from masks/graph
│   ├── scale_calibrator.py            # Pixel → metre
│   └── types.py                       # BuildingGraph Pydantic/dataclass models
│
├── topology/                          # Layer 4: Validation
│   ├── __init__.py
│   ├── validator.py                     # Rule engine
│   ├── repair.py                      # Auto-repair suggestions
│   ├── rules/                         # Individual rule modules
│   │   ├── wall_rules.py
│   │   ├── opening_rules.py
│   │   └── room_rules.py
│   └── types.py                       # ValidationReport models
│
├── bim_schema/                        # Layer 5: BIM JSON contract
│   ├── __init__.py
│   ├── models.py                      # BuildingAnalysis + extensions
│   ├── adapter.py                     # BuildingGraph → BuildingAnalysis
│   ├── type_maps.py                   # COMPONENT_TYPE_MAP, OPENING_TYPE_MAP
│   └── ifc_semantics.py               # Ported semantics from V3 ifc_properties (reference)
│
├── ifc_generator/                     # Layer 6: IFC compilation
│   ├── __init__.py
│   ├── v3_adapter.py                  # Read-only import of V3 build_detailed_ifc
│   ├── space_compiler.py              # IfcSpace from rooms (Phase 2)
│   └── compile.py                     # Public compile_ifc() entry point
│
├── viewer/                            # 3D + 2D visualization
│   ├── __init__.py
│   ├── ifc_viewer.py                  # Python launcher for static viewer
│   ├── overlay_viewer.py              # 2D detection overlay generator
│   └── static/                        # IFC.js + three.js assets
│       ├── index.html
│       ├── viewer.js
│       └── styles.css
│
├── training/                          # Training pipeline
│   ├── __init__.py
│   ├── dataset_manager.py             # Ingest, split, export YOLO yaml
│   ├── pseudo_labeler.py              # SVG → YOLO labels
│   ├── trainer.py                     # Ultralytics train/finetune wrapper
│   ├── evaluator.py                   # Metrics vs GT
│   └── callbacks.py                   # MLflow logging hooks
│
├── pipeline/                          # Orchestration
│   ├── __init__.py
│   ├── runner.py                      # PipelineRunner — full inference chain
│   ├── stages.py                      # Stage enum + dispatch
│   └── artifacts.py                   # Read/write per-stage JSON artifacts
│
├── dataset/                           # Local dataset storage (.gitignore contents)
│   ├── raw/                           # Downloaded floor plan images
│   ├── processed/                     # Preprocessed copies
│   ├── labels/                        # YOLO seg labels
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   ├── splits/                        # Split manifests (JSON)
│   ├── metadata/                      # Per-image sidecars
│   └── README.md                      # Dataset provenance + GDrive links
│
├── experiments/                       # Run outputs (.gitignore)
│   ├── runs/                          # MLflow / manual run dirs
│   │   └── {run_id}/
│   │       ├── config.yaml            # Frozen config snapshot
│   │       ├── preprocessed.png
│   │       ├── detections.json
│   │       ├── graph.json
│   │       ├── validation.json
│   │       ├── building.json
│   │       ├── model.ifc
│   │       └── overlay.jpg
│   └── baselines/                     # Gemini cache comparisons
│
├── scripts/                           # CLI entry points (thin wrappers)
│   ├── run_pipeline.py                # python scripts/run_pipeline.py --image ...
│   ├── ingest_dataset.py              # Download GDrive → dataset/raw
│   ├── train.py                       # Launch training
│   ├── evaluate.py                    # Run evaluator
│   ├── pseudo_label_svg.py            # Bootstrap from CubiCasa SVGs
│   └── compare_gemini.py              # Vision vs V3 cache baseline
│
├── tests/                             # Test suite
│   ├── fixtures/
│   │   ├── model_2.svg                # Symlink or copy reference
│   │   ├── golden_graph.json
│   │   └── golden_building.json
│   ├── unit/
│   │   ├── test_preprocess.py
│   │   ├── test_detection.py
│   │   ├── test_graph.py
│   │   ├── test_topology.py
│   │   └── test_bim_adapter.py
│   └── integration/
│       ├── test_pipeline_cubicasa.py
│       └── test_ifc_compile.py
│
└── docs/                              # Design documentation
    ├── README.md                      # Doc index
    ├── TECHNICAL_AUDIT_REPORT.md
    ├── ARCHITECTURE_ANALYSIS.md
    ├── HLD.md
    ├── LLD.md
    ├── TECH_STACK.md
    ├── FOLDER_STRUCTURE.md            # This file
    ├── DEVELOPMENT_ROADMAP.md
    └── DATASET_ANALYSIS.md            # Phase 2 (pending image inspection)
```

---

## 3. Module Dependency Graph

```
scripts/
    └── pipeline/runner.py
            ├── preprocessing/
            ├── detection/
            ├── graph_builder/
            ├── topology/
            ├── bim_schema/
            ├── ifc_generator/  ──(read-only)──▶ ../latest_interior_v1/
            └── viewer/

training/
    ├── dataset/          (reads/writes)
    ├── detection/        (model arch reference)
    └── pseudo_labeler/   ──▶ preprocessing/svg_parser.py
```

**Rule:** `bim_schema/` must not import from `ifc_generator/`. Dependency flows one way.

---

## 4. Config File: `configs/paths.yaml`

Reference paths to legacy projects (read-only):

```yaml
legacy:
  v3_compiler_root: "D:/HCI_interor/latest_interior_v1/latest_interior_v1"
  v3_ifc_properties: "D:/HCI_interor/latest_interior_v1/latest_interior_v1/ifc_properties.py"
  web_file_classes: "D:/HCI_interor/web_file/config/classes.py"
  cubicasa_svg_sample: "D:/HCI_interor/latest_interior/latest_interior/model_2.svg"
  gdrive_training_folder_id: "18IThRKRGUHFXnSiMtJlhqHSphDIuphNk"
  gdrive_era_folder_id: "17PW8x6zq37e0ize5PVLV4h9EPKWUjMxZ"
```

---

## 5. Gitignore Policy

```
# Data
dataset/raw/**
dataset/processed/**
dataset/labels/**
!dataset/README.md
!dataset/**/.gitkeep

# Experiments
experiments/**

# Models
detection/models/*.pt
*.pt
*.onnx

# Python
__pycache__/
.venv/
venv/
*.egg-info/

# MLflow
mlruns/

# Env
.env
```

---

## 6. Artifact Naming Convention

```
experiments/runs/{YYYYMMDD}_{HHMMSS}_{image_stem}/
```

| File | Stage | Format |
|------|-------|--------|
| `config.yaml` | orchestration | YAML |
| `preprocessed.png` | preprocess | PNG |
| `detections.json` | detect | JSON |
| `graph.json` | graph | JSON |
| `validation.json` | topology | JSON |
| `building.json` | bim | JSON |
| `model.ifc` | ifc | IFC STEP |
| `overlay.jpg` | viewer | JPEG |
| `metrics.json` | evaluate | JSON |

---

## 7. Package Layout (Python)

```
IMPROVED_MODEL_1/
  pyproject.toml   → name = "improved-model-1"
```

Installable package name: `improved_model_1` (import paths match folder names without hyphen).

**Phase 1:** Flat imports from project root via `PYTHONPATH=.` or editable install `pip install -e .`

---

## 8. Relationship to Legacy `gdrive_dataset`

| Legacy path | IMPROVED_MODEL_1 equivalent |
|-------------|------------------------------|
| `D:\HCI_interor\gdrive_dataset\` | `IMPROVED_MODEL_1\dataset\` |
| `images_raw/` | `dataset/raw/` |
| `images/train/` | `dataset/processed/` or symlink |
| `labels/train/` | `dataset/labels/train/` |
| `dataset.yaml` | `configs/dataset.yaml` (generated) |
| `marked/` | `experiments/runs/*/overlay.jpg` |
| `metadata/` | `dataset/metadata/` |
| `runs/` | `experiments/runs/` |

**Do not write into legacy `gdrive_dataset/`.** New pipeline is self-contained.

---

## 9. Implementation Order (Folder Creation)

| Order | Folder | When |
|-------|--------|------|
| 1 | `docs/` | ✅ Done |
| 2 | `configs/` | Week 1 Day 1 |
| 3 | `preprocessing/`, `tests/fixtures/` | Week 1 |
| 4 | `detection/` | Week 1–2 |
| 5 | `graph_builder/`, `topology/` | Week 2 |
| 6 | `bim_schema/`, `ifc_generator/` | Week 2–3 |
| 7 | `pipeline/`, `scripts/` | Week 3 |
| 8 | `training/`, `dataset/` | Week 3–4 |
| 9 | `viewer/` | Week 4 |

---

*End of Folder Structure*
