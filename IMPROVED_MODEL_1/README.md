# IMPROVED_MODEL_1

Vision-first AI training pipeline for **Floor Plan → BIM → IFC** generation.

Replaces LLM-only perception (Gemini) with a trainable, graph-based architecture while reusing the proven IFC compiler from `latest_interior_v1` as a read-only reference.

---

## Architecture

```
Floor Plan Image
      │
      ▼
┌─────────────────┐
│  Preprocessing  │  Normalize raster/SVG, deskew, resize
└────────┬────────┘
         ▼
┌─────────────────┐
│   Detection     │  YOLOv8-seg — walls, doors, windows, rooms  (planned)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Graph Builder  │  Pixel detections → metric building graph
└────────┬────────┘
         ▼
┌─────────────────┐
│   Topology      │  Architectural constraint validation
│   Validator     │
└────────┬────────┘
         ▼
┌─────────────────┐
│   BIM Schema    │  BuildingAnalysis JSON (V3-compatible)
└────────┬────────┘
         ▼
┌─────────────────┐
│  IFC Adapter    │  IfcOpenShell via V3 reference compiler
└────────┬────────┘
         ▼
    model.ifc  →  3D BIM Viewer
```

### Design principles

| Principle | Description |
|-----------|-------------|
| **Separation of perception and compilation** | Vision models evolve independently of the IFC layer |
| **Schema as contract** | `BuildingAnalysis` JSON is the single interchange format |
| **Dual representation** | Pixel masks for training; metre centerlines for BIM |
| **Deterministic geometry** | Graph operations are rule-based and testable |
| **No legacy modification** | Reference projects are read-only; adapters import V3 code |

---

## Project structure

```
IMPROVED_MODEL_1/
├── src/
│   ├── dataset_tools/       Audit, deduplication, split creation
│   ├── preprocessing/       Image load, enhance, normalize
│   ├── graph_builder/       Detection → BuildingGraph
│   ├── topology_validator/  Rule-based graph validation
│   ├── bim_schema/          BuildingAnalysis Pydantic models
│   ├── ifc_adapter/         IfcOpenShell / V3 compiler wrapper
│   ├── pipeline/            End-to-end orchestration
│   └── tests/               Unit and integration tests
├── data/                    Raw Era floor plan corpus (read-only source)
├── docs/                    Design documents and audit reports
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Requirements

- **Python 3.11**
- OpenCV (`opencv-python-headless`)
- NetworkX
- Shapely
- Pydantic v2
- IfcOpenShell ≥ 0.8

---

## Setup

```bash
cd D:\HCI_interor\IMPROVED_MODEL_1

python -m venv .venv
.venv\Scripts\activate        # Windows

pip install -r requirements.txt
pip install -e ".[dev]"       # editable install + pytest
```

Set `PYTHONPATH` for development without editable install:

```bash
set PYTHONPATH=D:\HCI_interor\IMPROVED_MODEL_1\src
```

---

## Module overview

| Module | Entry point | Responsibility |
|--------|-------------|----------------|
| `dataset_tools` | `DatasetAuditor`, `DatasetCleaner` | Scan, deduplicate, normalize, split |
| `preprocessing` | `ImagePreprocessor` | Format conversion, deskew, resize |
| `graph_builder` | `BuildingGraphBuilder` | Wall graph, openings, rooms, scale |
| `topology_validator` | `TopologyValidator` | Constraint checks before BIM export |
| `bim_schema` | `BuildingAnalysis` | Canonical BIM JSON schema |
| `ifc_adapter` | `IFCCompilerAdapter` | JSON → IFC4 via V3 reference |
| `pipeline` | `PipelineRunner` | Stage orchestration + artifacts |

All core methods currently raise `NotImplementedError` — this is the **Phase 0 skeleton**.

---

## Usage (planned)

```python
from pathlib import Path
from pipeline import PipelineRunner, PipelineConfig

runner = PipelineRunner(PipelineConfig(artifacts_dir=Path("experiments/runs")))
result = runner.run(Path("data/plan.jpg"))
print(result.ifc_path)
```

```python
from pathlib import Path
from dataset_tools import DatasetAuditor, DatasetAuditConfig

report = DatasetAuditor(DatasetAuditConfig(root=Path("data"))).run()
print(report.total_files, report.unique_content_count)
```

---

## Dataset

Raw floor plans live in `data/` (~315 unique images after deduplication). See:

- [`docs/DATASET_AUDIT.md`](docs/DATASET_AUDIT.md) — full corpus analysis
- [`docs/HLD.md`](docs/HLD.md) — high-level design
- [`docs/LLD.md`](docs/LLD.md) — module interfaces

**Important:** Exclude `data/Era/` when training — it duplicates root-level files.

---

## Reference implementations (read-only)

| Project | Role |
|---------|------|
| `latest_interior_v1/` | V3 IFC compiler + `BuildingAnalysis` schema |
| `web_file/` | YOLO training UI + 17-class taxonomy |
| `latest_interior/model_2.svg` | CubiCasa vector bootstrap |

These projects are **not modified** by IMPROVED_MODEL_1.

---

## Development status

| Phase | Status |
|-------|--------|
| Design docs | Complete |
| Dataset audit | Complete |
| Source skeleton | **Current** |
| Preprocessing implementation | Pending |
| Detection layer (YOLO) | Pending |
| Graph + topology | Pending |
| IFC adapter wiring | Pending |
| Training pipeline | Pending |

---

## Testing

```bash
pytest src/tests -v
```

---

## License

Internal HCI Interior project — not for external distribution.
