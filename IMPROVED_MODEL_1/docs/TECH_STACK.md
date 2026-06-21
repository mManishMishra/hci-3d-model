# Recommended Technology Stack

**Project:** IMPROVED_MODEL_1  
**Version:** 1.0  
**Date:** 2026-06-09

---

## 1. Stack Overview

| Layer | Primary Choice | Alternatives | Rationale |
|-------|---------------|--------------|-----------|
| Language | Python 3.11 | 3.10 | Matches existing venv; ML ecosystem |
| Detection | Ultralytics YOLOv8-seg | YOLO11-seg, RT-DETR | Already in `web_file`; fast iteration |
| Deep Learning | PyTorch 2.x | — | Ultralytics dependency |
| Graph / Geometry | NetworkX + Shapely | CGAL bindings | Pure Python, testable |
| OCR | PaddleOCR | EasyOCR, Tesseract | Strong on mixed EN/metric text |
| Image IO | OpenCV + Pillow | — | Existing codebase convention |
| SVG | CairoSVG + lxml | svgpathtools | CubiCasa parse + rasterize |
| Schema | Pydantic v2 | dataclasses | V3 compatibility |
| IFC | IfcOpenShell 0.8.x | — | Existing V1–V3 standard |
| Viewer | IFC.js (web-ifc) | xeokit, That Open Company | Browser-native, no install |
| API (optional) | FastAPI | Flask | Proven in `web_file` |
| Config | YAML + Hydra | OmegaConf | Experiment reproducibility |
| Experiment tracking | MLflow | Weights & Biases | Local-first, free |
| Data versioning | DVC | Git LFS | Large image datasets |
| Testing | pytest | unittest | Standard |
| Linting | ruff | flake8 | Fast |
| Type checking | mypy (optional) | pyright | Gradual adoption |
| Containerization | Docker | — | Phase 3 deployment |
| Annotation | CVAT (self-hosted) | Label Studio | Industry standard for seg |

---

## 2. Layer-by-Layer Stack

### 2.1 Image Preprocessing

| Component | Package | Version (pin) |
|-----------|---------|---------------|
| Image arrays | `numpy` | ≥1.24 |
| CV operations | `opencv-python-headless` | ≥4.8 |
| SVG rasterize | `cairosvg` | ≥2.7 |
| SVG parse | `lxml` | ≥4.9 |
| Deskew | `opencv-python` + custom | — |
| Thinning | `opencv-contrib-python` (`ximgproc`) | ≥4.8 |

### 2.2 Detection

| Component | Package | Version (pin) |
|-----------|---------|---------------|
| YOLO framework | `ultralytics` | ≥8.2 |
| PyTorch | `torch` | ≥2.1 (CUDA optional) |
| Torchvision | `torchvision` | matching torch |
| NMS / masks | `ultralytics` built-in | — |
| Export | ONNX via `ultralytics.export` | Phase 2 |

**GPU recommendation:** NVIDIA GPU with ≥8GB VRAM for training; CPU sufficient for nano model inference during dev.

**Initial model:** `yolov8n-seg.pt` (nano) → scale to `yolov8m-seg.pt` if accuracy insufficient.

### 2.3 OCR (Scale + Room Labels)

| Component | Package | Notes |
|-----------|---------|-------|
| OCR engine | `paddlepaddle` + `paddleocr` | CPU mode acceptable for dev |
| Text parsing | `regex` | Dimension patterns: `\d+\.\d+\s*m` |
| Unit conversion | custom | Imperial → metric in parser |

**Defer to Phase 2** if CubiCasa SVG bootstrap covers initial training data.

### 2.4 Building Graph

| Component | Package | Purpose |
|-----------|---------|---------|
| Graph structure | `networkx` | Nodes, edges, cycles |
| Polygon ops | `shapely` | Room validity, intersection |
| Spatial index | `shapely.strtree` | Fast nearest-wall queries |
| Numerics | `numpy` | Coordinate transforms |

### 2.5 Topology Validation

| Component | Package | Purpose |
|-----------|---------|---------|
| Geometry checks | `shapely` | Closed, simple, area |
| Rules engine | Custom Python | No external deps |
| Reporting | Pydantic models | Structured errors |

### 2.6 BIM Schema

| Component | Package | Purpose |
|-----------|---------|---------|
| Models | `pydantic` ≥2.0 | `BuildingAnalysis` |
| JSON IO | `orjson` (optional) | Fast serialization |
| Validation | Pydantic + JSON Schema export | API contracts |

### 2.7 IFC Generation

| Component | Package | Purpose |
|-----------|---------|---------|
| IFC writer | `ifcopenshell` ≥0.8.0 | IFC4 output |
| V3 adapter | importlib + sys.path | Read-only reference to `latest_interior_v1` |

**Do not bundle** `floorplan_ifc_ai/venv`. Create fresh `requirements.txt` in `IMPROVED_MODEL_1`.

### 2.8 3D Viewer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| IFC parsing | `web-ifc` (npm) | Browser IFC loader |
| Rendering | `three.js` | 3D scene |
| Host page | Static HTML or Vite | `viewer/static/` |
| Dev preview | `streamlit` (optional) | Quick Python-side preview |

**Alternative (Python-native):** IfcOpenShell + `ifcopenshell.geom` → glTF export → three.js. Heavier but no WASM dependency.

**Recommended for Phase 1:** IFC.js static page served by `python -m http.server` or FastAPI static mount.

### 2.9 Training Infrastructure

| Component | Package | Purpose |
|-----------|---------|---------|
| Training | `ultralytics` YOLO.train() | Segmentation |
| Augmentation | Ultralytics built-in + Albumentations (optional) | Floor plan aug |
| Split management | `sklearn.model_selection` | Stratified splits |
| Metrics | `torchmetrics` | IoU, mAP |
| Logging | `mlflow` | Experiments |
| Config | `hydra-core` | Composable configs |
| Parallel download | `gdown` | GDrive dataset ingest |

### 2.10 Annotation Tooling

| Phase | Tool | Use case |
|-------|------|----------|
| Phase 1 | CubiCasa SVG parser | Auto pseudo-labels |
| Phase 2 | CVAT | Human polygon correction |
| Phase 3 | Custom overlay viewer | In-house review (inspired by `web_file`) |

---

## 3. `requirements.txt` Structure (Design)

```
# Core
python>=3.11,<3.13
numpy>=1.24
opencv-python-headless>=4.8
pillow>=10.0
pydantic>=2.5
pyyaml>=6.0
shapely>=2.0
networkx>=3.2

# Detection
ultralytics>=8.2
torch>=2.1
torchvision>=0.16

# IFC
ifcopenshell>=0.8.0

# SVG / OCR (optional extras)
cairosvg>=2.7
lxml>=4.9
# paddleocr  # Phase 2

# Training ops
mlflow>=2.10
scikit-learn>=1.3
gdown>=5.0

# Dev
pytest>=7.4
ruff>=0.3
```

Separate `requirements-gpu.txt` for CUDA-specific torch builds.

---

## 4. Hardware Recommendations

| Workload | Minimum | Recommended |
|----------|---------|-------------|
| Development | 16GB RAM, CPU | 32GB RAM, RTX 3060 12GB |
| YOLO training (nano) | CPU (slow) | RTX 3070+ |
| YOLO training (medium) | RTX 3080 10GB | RTX 4090 24GB |
| Batch inference | CPU | GPU |
| IFC compile | CPU | CPU (fast enough) |
| Viewer | Any modern browser | Chrome/Edge with WebGL2 |

---

## 5. What We Explicitly Do NOT Use (Phase 1)

| Technology | Reason |
|------------|--------|
| Gemini / LLM for perception | Target architecture removes hallucination source |
| MongoDB / Redis | File-based artifacts sufficient for Phase 1 |
| Kubernetes | Premature; Docker first |
| Custom C++ inference | YOLO ONNX export is Phase 2+ |
| Revit / ArchiCAD APIs | Out of scope; IFC is interchange format |
| NeRF / 3D diffusion | Future interior phase only |

---

## 6. Future Stack Extensions

### 6.1 Multimodal Training

| Component | Choice |
|-----------|--------|
| Vision encoder | YOLO backbone features or ViT |
| Text encoder | `sentence-transformers` for OCR labels |
| Graph encoder | PyTorch Geometric (GNN) |
| Fusion | Cross-attention transformer |

### 6.2 Interior Generation

| Component | Choice |
|-----------|--------|
| Layout diffusion | Custom U-Net on room masks |
| LLM (optional) | Style/material suggestions only — not geometry |
| Asset library | Parametric furniture meshes → `IfcFurniture` |

### 6.3 Production Deployment

| Component | Choice |
|-----------|--------|
| API | FastAPI + uvicorn |
| Queue | Celery + Redis (batch jobs) |
| Model serving | Triton or ONNX Runtime |
| Storage | S3-compatible object store |
| CI | GitHub Actions |

---

## 7. Compatibility with Legacy Projects

| Legacy dep | IMPROVED_MODEL_1 approach |
|------------|---------------------------|
| `google-genai` | Not required for core pipeline; optional for baseline comparison experiments |
| `web_file` Ultralytics version | Pin same major version to reuse any existing `best_gdrive.pt` if found |
| V3 IfcOpenShell | Match ≥0.8.0 for compatible IFC output |
| V3 Pydantic models | Copy schema; do not cross-import at training time |

---

## 8. Decision Log

| Decision | Options considered | Choice | Why |
|----------|-------------------|--------|-----|
| Detection framework | YOLO, Mask R-CNN, SAM | YOLOv8-seg | Existing `web_file` investment; fast train |
| Graph library | NetworkX, igraph | NetworkX | Simpler API, sufficient scale |
| IFC compiler | Rewrite, V3 adapter | V3 adapter | User constraint; V3 is mature |
| Viewer | Blender, IFC.js | IFC.js | Zero install for reviewers |
| OCR timing | Phase 1 vs 2 | Phase 2 | SVG bootstrap covers early data |
| Config | JSON, Hydra, YAML | YAML + Hydra | Readable; composable experiments |

---

*End of Recommended Technology Stack*
