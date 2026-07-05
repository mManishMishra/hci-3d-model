# Low-Level Design (LLD)

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19  
**Scope:** Training pipeline modules only

---

## 1. Overview

This document specifies module interfaces, data structures, and interaction contracts for the **YOLO11 floor-plan segmentation training system**. It covers dataset preparation, annotation export, training, and evaluation.

**Out of scope:** any modules or data types for downstream processing beyond mask prediction.

---

## 2. Core Data Types

### 2.1 `PreprocessedImage`

```yaml
image_id: str              # UUID or content hash
source_path: str
source_format: str           # jpg | png | ...
width: int                   # pixels after preprocess
height: int
tensor_path: str             # saved normalized array or PNG
metadata:
  deskew_angle: float
  binarized: bool
```

**Implementation:** `src/preprocessing/image_preprocessor.py` — `PreprocessedImage` dataclass.

### 2.2 `YoloSegLabel`

One instance per polygon line in a `.txt` file:

```yaml
class_id: int               # 0=wall, 1=door, 2=window
normalized_coords: list[float]  # x1 y1 x2 y2 ... xn yn in [0,1]
vertex_count: int           # >= 3 (recommend >= 4)
```

**File format (YOLO 1.1 segmentation):**

```
<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>
```

### 2.3 `LabelFile`

```yaml
image_stem: str
split: train | val
path: Path                   # labels/{split}/{stem}.txt
instances: list[YoloSegLabel]
is_valid: bool
validation_errors: list[str]
```

### 2.4 `DatasetManifest`

```yaml
batch_name: str              # e.g. prototype_11_batch
images_root: Path
labels_root: Path
entries:
  - rank: int
    filename: str
    split: train | val
    annotated: bool
    label_path: str | null
```

**Source:** `data/prototype_11_batch/manifest.csv`

### 2.5 `TrainingConfig`

```yaml
model: str                   # yolo11n-seg.pt
data_yaml: Path
epochs: int                  # 50
batch: int                   # 4
imgsz: int                   # 1024
device: str                  # cuda:0 | cpu
project: Path                # runs/prototype
name: str
patience: int                # 15
augment:
  mosaic: float             # 1.0
  degrees: float             # 5.0
  fliplr: float              # 0.5
```

### 2.6 `EvaluationReport`

```yaml
model_path: Path
val_images: int
metrics:
  wall:
    map50: float
    map50_95: float
  door:
    map50: float
  window:
    map50: float
  overall_map50: float
legacy_comparison:
  web_file_map50: float | null
  delta: float | null
passed_qc: bool
```

---

## 3. Module Specifications

### 3.1 `ImagePreprocessor`

| | |
|---|---|
| **Path** | `src/preprocessing/image_preprocessor.py` |
| **Status** | Implemented |

```python
class ImagePreprocessor:
    def process(self, source_path: Path) -> PreprocessedImage: ...
    def deskew(self, image: np.ndarray) -> tuple[np.ndarray, float]: ...
    def resize(self, image: np.ndarray) -> np.ndarray: ...
```

**Use in training:** Optional pre-train normalization; not required if annotating on original rasters.

---

### 3.2 `DatasetCleaner`

| | |
|---|---|
| **Path** | `src/dataset_tools/dataset_cleaner.py` |
| **Status** | Partial |

```python
class DatasetCleaner:
    def run(self) -> DatasetCleanReport: ...
    def deduplicate(self, paths: list[Path]) -> list[Path]: ...
    def create_splits(self, image_paths: list[Path]) -> dict[str, list[Path]]: ...
    # create_splits — NotImplementedError (planned)
```

**Responsibilities:**

- Collect raster images from source corpus
- MD5 deduplication
- Normalize extensions (JFIF → JPG)
- Exclude `Era/` duplicates
- Emit split manifest

---

### 3.3 `LabelValidator` (planned)

| | |
|---|---|
| **Path** | `scripts/validate_labels.py` |
| **Status** | Not implemented |

```python
def validate_label_file(path: Path, nc: int = 3) -> list[str]: ...
def validate_dataset(data_yaml: Path) -> ValidationReport: ...
```

**Checks:**

- Every image has paired `.txt`
- `class_id ∈ {0, 1, 2}`
- ≥ 7 tokens per line (1 class + 6 coords)
- All coordinates ∈ [0, 1]
- No empty files for annotated images

---

### 3.4 `YOLOTrainer` (planned)

| | |
|---|---|
| **Path** | `scripts/train.py` → future `src/training/trainer.py` |
| **Status** | Not implemented |

```python
def train(config: TrainingConfig) -> Path:
    """Returns path to best.pt weights."""
```

**Behavior:**

1. Load `dataset.yaml`; abort if val path == train path
2. Verify labels via `LabelValidator`
3. `YOLO(config.model).train(...)` via Ultralytics
4. Log metrics to `runs/{project}/{name}/`
5. Return `weights/best.pt`

**Reference:** Port patterns from `web_file/web/server.py` `_train_worker` (callbacks, SSE optional).

---

### 3.5 `Evaluator` (planned)

| | |
|---|---|
| **Path** | `scripts/evaluate.py` |
| **Status** | Not implemented |

```python
def evaluate(model_path: Path, data_yaml: Path) -> EvaluationReport: ...
def compare_legacy(val_dir: Path, improved_weights: Path, legacy_weights: Path) -> dict: ...
```

**Metrics:** mask mAP50, mAP50-95 per class (wall, door, window). No topology or compilation metrics.

---

### 3.6 `DraftAnnotator` (helper only)

| | |
|---|---|
| **Path** | `scripts/cursor_draft_annotator.py` |
| **Status** | Implemented (heuristic) |

**Not ground truth.** Produces draft polygons for human correction in CVAT only.

---

## 4. Data Flow

### 4.1 Annotation → Export

```
CVAT project (IMPROVED_MODEL_1_Structural_Seg)
    │  polygon labels: wall, door, window
    ▼
Export YOLO 1.1 segmentation
    │  verify class ID remap (wall=0, door=1, window=2)
    ▼
labels/train/*.txt  +  labels/val/*.txt
    │
    ▼
validate_labels.py → QC report
```

### 4.2 Training

```
dataset.yaml (nc=3, train≠val)
    │
    ▼
train.py --data dataset.yaml --model yolo11n-seg.pt --imgsz 1024
    │
    ▼
runs/prototype/weights/best.pt
    │
    ▼
evaluate.py --compare-legacy web_file checkpoint
```

---

## 5. Directory Layout (Training Scope)

```
data/prototype_11_batch/
├── images/
│   ├── train/          # ranks 1–20
│   └── val/            # ranks 21–25
├── labels/
│   ├── train/
│   └── val/
├── manifest.csv
└── dataset.yaml        # create at export time

runs/
└── prototype/
    └── weights/
        └── best.pt
```

---

## 6. CVAT Integration

| Setting | Value |
|---------|-------|
| Project name | `IMPROVED_MODEL_1_Structural_Seg` |
| Labels | wall `#FF0000`, door `#00CC00`, window `#0066FF` |
| Tool | Polygon only |
| Export | YOLO 1.1 segmentation |

See [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) §7–8.

---

## 7. Legacy Interface Mapping

| Legacy (`web_file`) | IMPROVED_MODEL_1 |
|---------------------|------------------|
| `contour_to_yolo_seg()` | Reuse format; same line structure |
| `CLASS_IDS` 17-class | Replace with 3-class `prototype_classes.yaml` |
| `train=val=test` in dataset.yaml | **Forbidden** |
| `FloorPlanDetector` mock | **Not used** — CVAT human labels |
| `_train_worker` | Port to `scripts/train.py` |
| YOLOv8n-seg | Upgrade to YOLO11n-seg |

---

## 8. Error Handling

| Condition | Action |
|-----------|--------|
| Missing label for image | Block training; list in validation report |
| class_id > 2 | Block training; likely CVAT remap error |
| val dir empty | Block training |
| train dir == val dir | Block training; legacy anti-pattern |
| < 4 vertices on polygon | Warning; allow if ≥ 3 (YOLO minimum) |

---

## 9. Testing Strategy

| Test | Location | Coverage |
|------|----------|----------|
| Preprocessor unit tests | `src/tests/test_image_preprocessor.py` | ✅ |
| Dataset cleaner tests | `src/tests/test_dataset_cleaner.py` | ✅ |
| Label validation tests | `src/tests/test_validate_labels.py` | Planned |
| Train smoke test | CI optional | 1 epoch on 2 images |

---

## 10. Deferred Modules (Not in LLD v2)

The following exist as stubs in `src/` but are **out of scope** for the current LLD and must not appear in training-critical paths:

- `src/graph_builder/`
- `src/topology_validator/`
- `src/bim_schema/`
- `src/ifc_adapter/`
- `src/pipeline/run_pipeline.py` (full-stack orchestration)

These stubs are not specified here and must not influence training milestone delivery.

---

*LLD v2 — segmentation training scope only. Supersedes LLD v1 (2026-06-09).*
