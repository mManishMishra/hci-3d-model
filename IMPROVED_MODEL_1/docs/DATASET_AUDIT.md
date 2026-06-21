# Dataset Audit Report

**Location audited:** `D:\HCI_interor\IMPROVED_MODEL_1\data`  
**Audit date:** 2026-06-10  
**Method:** Read-only recursive scan (MD5 hashing, dimension analysis, content sampling)  
**Auditor:** IMPROVED_MODEL_1 pipeline design phase

---

## 1. Executive Summary

The `data/` folder contains **570 files** representing approximately **349 unique assets** after deduplication. The dataset is an **unlabeled collection of raster floor plan images** sourced from the **Era** Google Drive corpus ([Era folder](https://drive.google.com/drive/folders/17PW8x6zq37e0ize5PVLV4h9EPKWUjMxZ)), plus **34 furniture-layout PDFs**.

| Finding | Status |
|---------|--------|
| Raw floor plan images | **315 unique** (536 file entries with duplicates) |
| Annotations (YOLO/COCO/LabelMe/CVAT) | **None** |
| Train/val/test splits | **None** |
| CAD (DWG/DXF) | **None** |
| SVG floor plans | **None** |
| IFC models | **None** |
| Duplicate storage | **221 redundant file copies** (~39% of all files) |

**Bottom line:** This dataset is suitable as a **raw image corpus for prototype training pipeline development**, but requires deduplication, labeling, and split creation before any supervised YOLO training can begin.

---

## 2. Folder Tree Summary

```
D:\HCI_interor\IMPROVED_MODEL_1\data\
├── [367 files]          # Root-level flat dump (images + PDFs)
│   ├── *.jpg            # 333 image entries (incl. duplicates)
│   ├── *.jfif           # Mixed with jpg
│   ├── *.pdf            # 34 furniture layout PDFs
│   └── *.gif            # 2 animated/static floor plan GIFs
│
└── Era\                 # [203 files] — DUPLICATE SUBSET of root
    ├── *.jpg
    └── *.jfif           # Same filenames as root; 100% content match
```

### 2.1 Structure Characteristics

| Property | Value |
|----------|-------|
| **Depth** | 2 levels (root + `Era/` only) |
| **Subfolders** | 1 (`Era/`) |
| **Organization** | Flat — no `train/`, `val/`, `labels/`, or `images/` hierarchy |
| **Naming** | UUID-style (168), MD5-hex (139), copy suffixes `(1)` (21 files) |
| **All files modified** | 2026-06-10 (single bulk download/import event) |

There are **no annotation subdirectories**, no `dataset.yaml`, and no metadata sidecars.

---

## 3. File Counts by Extension

### 3.1 Requested Extensions

| Extension | File count | Notes |
|-----------|------------|-------|
| `.jpg` | **368** | Primary raster format |
| `.jpeg` | **0** | — |
| `.png` | **0** | — |
| `.tif` | **0** | — |
| `.tiff` | **0** | — |
| `.svg` | **0** | — |
| `.dwg` | **0** | — |
| `.dxf` | **0** | — |
| `.ifc` | **0** | — |
| `.json` | **0** | — |
| `.txt` | **0** | — |
| `.xml` | **0** | — |
| `.yaml` | **0** | — |
| `.yml` | **0** | — |

### 3.2 Additional Extensions Found

| Extension | File count | Role |
|-----------|------------|------|
| `.jfif` | **166** | JPEG variant — same MIME family as `.jpg` |
| `.pdf` | **34** | Furniture/interior layout documents |
| `.gif` | **2** | Floor plan images (GIF container) |

### 3.3 Combined Totals

| Category | File entries | Unique content (MD5) |
|----------|--------------|----------------------|
| Raster images (jpg + jfif + gif) | **536** | **315** |
| PDF documents | **34** | **34** |
| **Grand total** | **570** | **349** |
| Redundant copies | **221** | — |

**Effective unique raster formats:** `.jpg` (216 unique), `.jfif` (97 unique), `.gif` (2 unique).

---

## 4. Annotation Format Detection

All standard annotation formats were searched by **file extension** and **directory naming convention**.

| Format | Detected | Evidence |
|--------|----------|----------|
| **YOLO** | **No** | 0 `.txt` label files; no `labels/` directory |
| **COCO** | **No** | 0 `.json` files; no `annotations/` directory |
| **LabelMe** | **No** | 0 LabelMe JSON; no polygon sidecars |
| **CVAT** | **No** | 0 CVAT XML exports |
| **Custom JSON** | **No** | 0 JSON files of any kind |

### 4.1 Implicit Labels in Images

Visual inspection of sampled images confirms that **text annotations are embedded in the raster** (room names, dimensions, ceiling heights) but are **not extracted** into any machine-readable label file. OCR will be required to leverage this information.

**Conclusion:** The dataset is **100% unlabeled** from a machine learning perspective.

---

## 5. Asset Classification

### 5.1 Raw Floor Plan Images

| Metric | Value |
|--------|-------|
| Unique images | **315** |
| Formats | JPG (69%), JFIF (31%), GIF (<1%) |
| Content type | Architectural floor plans — residential, commercial |
| Visual styles | ~**297** B&W line/CAD drawings; ~**18** color rendered plans |
| Furnishing detail | Mixed — bare structural to fully furnished layouts |

**Sample observations (visual audit):**

| Sample file | Style | Content |
|-------------|-------|---------|
| `0ac1b0c3539d4a56b1acdaf5f4cad477.jpg` | Color furnished | Multi-bedroom upper floor with dimensions (ft/in) |
| `02847614ca21d569824f26d8c264cb39.jpg` | B&W line | 4-bedroom house, standard architectural symbols |
| `009b1b7a-ff37-4d1a-9d6c-47b8bd4862b2.jfif` | B&W CAD | Modern house with metric dims + ceiling heights |
| `034c4f79227c02d36596aae1afd3ecea.jpg` | Color rendered | Ground floor with furniture + human figures |
| `d0ff4023c2f57fd1420831b256ba771a.gif` | B&W line | Large residential plan (~93' × 80') |

**Dimension systems observed:** Mixed **imperial (ft/in)** and **metric (mm/m)** — scale calibration will be non-trivial.

### 5.2 Annotated Floor Plans

**Count: 0**

No images with overlaid bounding boxes, segmentation masks, or companion label files exist in this directory.

### 5.3 CAD Drawings

**Count: 0**

No `.dwg`, `.dxf`, or vector CAD source files. All geometry is rasterized.

### 5.4 SVG Floor Plans

**Count: 0** in `data/`

**External supplement available:** `D:\HCI_interor\latest_interior\latest_interior\model_2.svg` (CubiCasa v1.1, 1514×1312 units) — not part of this audit path but recommended for pseudo-label bootstrap.

### 5.5 IFC Models

**Count: 0**

No `.ifc` files in `data/`.

### 5.6 PDF Documents (Furniture Layouts)

| Metric | Value |
|--------|-------|
| Count | **34** (all in root, none in `Era/`) |
| Content | **100% furniture/interior layout PDFs** |
| Naming pattern | `*FURNITURE LAYOUT*`, `*furniture layout*` |
| Size range | 127 KB – 1,058 KB |

**Examples:**
- `APARNA HOMES FURNITURE LAYOUT-Model 1.pdf`
- `OFFICE FURNITURE LAYOUT.pdf`
- `REVISED FURNITURE LAYOUT @SEC 106 GURUGRAM.pdf`

These are **interior design deliverables**, not structural/architectural floor plan sources. They belong to a **future interior generation track**, not the wall/door/window detection prototype.

---

## 6. Image Resolution and Size Analysis

Analysis performed on **315 unique images** (deduplicated by MD5).

| Metric | Width (px) | Height (px) | File size (KB) |
|--------|------------|-------------|----------------|
| **Minimum** | 236 | 275 | 15.8 |
| **Maximum** | 1,200 | 1,993 | 240.6 |
| **Mean** | 674 | 861 | 78.3 |
| **Aspect ratio range** | 0.28 – 1.78 | — | — |

### 6.1 Resolution Distribution (Megapixels)

| Bucket | Count | % |
|--------|-------|---|
| < 0.1 MP | 3 | 1% |
| 0.1 – 0.5 MP | 136 | 43% |
| 0.5 – 1.0 MP | 139 | 44% |
| 1.0 – 4.0 MP | 37 | 12% |
| > 4.0 MP | 0 | 0% |

**Implication:** 87% of images are below 1 megapixel. Fine wall/door detail may be lost at YOLO default `imgsz=640`. Consider `imgsz=1024` or super-resolution preprocessing for production.

---

## 7. Train / Val / Test Splits

| Split | Present | Path |
|-------|---------|------|
| Train | **No** | — |
| Validation | **No** | — |
| Test | **No** | — |

No split manifests, no `dataset.yaml`, and no stratification metadata exist.

**Recommendation:** Create splits in `IMPROVED_MODEL_1/dataset/` (not in `data/`) after deduplication:

```
dataset/
├── raw/              # 315 deduplicated images (symlinks or copies)
├── labels/train/     # To be created
├── labels/val/
├── labels/test/
└── splits/manifest.json
```

Suggested initial ratio: **70 / 20 / 10** stratified by visual style (B&W vs color).

---

## 8. Duplicate Detection

### 8.1 Exact Duplicates (MD5)

| Duplicate type | Groups | Redundant files |
|----------------|--------|-----------------|
| Root ↔ `Era/` copy | **195** unique images | **195** |
| `(1)` copy suffix (same content as base) | **~12** unique images | **~12** |
| Other exact MD5 matches | **~14** | **~14** |
| **Total redundant** | **202 groups** | **221 files** |

Every file in `Era/` has an **identical copy** at the root level (203/203 filename match, 0 content differences).

```
data/02847614ca21d569824f26d8c264cb39.jpg
data/Era/02847614ca21d569824f26d8c264cb39.jpg   ← exact MD5 match
```

### 8.2 Root-Only Images (Not in Era/)

**127 images** exist only at root level — these are **not duplicated** into `Era/`. The `Era/` subfolder contains 195 of the 315 unique images (62%), not the full set.

### 8.3 Near-Duplicates (Same Dimensions + Size)

Clustering by `(width, height, size_kb)` found **0 groups** with more than one unique image — no obvious near-duplicate floor plans beyond exact copies.

### 8.4 Cross-Dataset Duplicates

Comparison with other workspace locations:

| Location | Files scanned | MD5 overlap with `data/` |
|----------|---------------|--------------------------|
| `D:\HCI_interor\gdrive_dataset\images_raw\` | 26 images | **3 images** |
| `D:\HCI_interor\latest_interior\latest_interior\` | 7 files | **0** |

**Overlapping filenames (gdrive_dataset ↔ data):**
- `1_bhk_flat.jpg` ↔ `2b9aabd5-a08a-414c-ba70-b305490635b8.jpg`
- `1_BHK_HOUSE.jpg` ↔ `1f7dd3f5-6bea-42be-b36c-6c90aa060737.jpg`
- `3f7c92bf-4817-496d-a242-91195f24726b.jpg` (same name and hash)

**Conclusion:** `data/` is largely independent of `gdrive_dataset/` but shares 3 files. The `Era/` subfolder is an **internal duplicate dataset** and should be excluded from training.

---

## 9. Content Quality Assessment

### 9.1 Strengths

1. **Large unlabeled corpus** — 315 unique floor plans for prototype scale
2. **Real-world diversity** — varied drawing styles, room counts, furnishing levels
3. **Mixed BHK/residential types** — suitable for generalization testing
4. **Embedded text** — room labels and dimensions available for OCR supervision
5. **Consistent with documented Era GDrive source**

### 9.2 Weaknesses

1. **Zero ground-truth annotations**
2. **39% redundant storage** (root + Era/ duplication)
3. **Low resolution** — majority under 1 MP
4. **Mixed unit systems** — imperial and metric in same corpus
5. **High style variance** — B&W CAD vs color renders vs furnished
6. **No vector sources** — harder to bootstrap precise wall centerlines
7. **PDFs are wrong task** — furniture layouts, not structural plans
8. **Flat organization** — no metadata (BHK count, source project, etc.)
9. **Opaque filenames** — UUID/MD5 names complicate manual review

---

## 10. Recommended Dataset for Prototype

### 10.1 Primary: Deduplicated Raster Corpus

| Property | Recommendation |
|----------|----------------|
| **Source path** | `data/` root files only — **exclude `data/Era/`** |
| **After dedup** | **315 unique images** |
| **Exclude** | 21 `(1)` copy files (exact duplicates of base) |
| **Effective clean set** | **~303 unique images** (315 minus ~12 `(1)` unique hashes already counted) |
| **Format normalization** | Convert `.jfif` → `.jpg` during ingest |
| **GIF handling** | Extract first frame → PNG/JPG |

### 10.2 Supplement: Vector Ground Truth

| Source | Purpose |
|--------|---------|
| `latest_interior/latest_interior/model_2.svg` | CubiCasa pseudo-label bootstrap |
| Future SVG exports | High-quality wall/room/opening GT |

### 10.3 Prototype Workflow (Suggested)

```
Phase A — Bootstrap (no manual labeling):
  model_2.svg → pseudo YOLO labels → sanity check pipeline

Phase B — Small labeled set:
  Select 30 diverse images from 315 (stratified by style)
  → CVAT polygon annotation (Wall, Door, Window, Room)
  → Train YOLOv8n-seg baseline

Phase C — Scale:
  Pseudo-label 315 images with trained model
  → Human review queue for low-confidence
  → Expand to 100+ verified labels
```

### 10.4 Images to Prioritize for First Manual Label Batch

Select from these **style buckets**:

| Bucket | ~Count | Why |
|--------|--------|-----|
| B&W bare architectural | ~200 | Closest to detection target; clearest walls |
| B&W furnished | ~80 | Tests furniture class separation |
| Color rendered | ~18 | Harder; defer to Phase 2 |
| GIF | 2 | Convert first; low priority |

### 10.5 Exclude from Structural Detection Prototype

| Asset | Reason |
|-------|--------|
| `data/Era/**` | Exact duplicates — wastes training I/O |
| `*.pdf` (34 files) | Furniture layouts; different pipeline stage |
| `(1)` copy files | Exact MD5 duplicates |

---

## 11. Risks and Issues

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R1 | **No labels** — cannot train supervised model | Critical | CubiCasa SVG bootstrap + CVAT labeling sprint |
| R2 | **Era/ duplication** — 39% wasted storage; risk of train/val leakage if both used | High | Deduplicate on ingest; single canonical copy |
| R3 | **Low resolution** — wall thickness in pixels may be 1–3px | High | `imgsz=1024`; selective upscaling; reject <400px short edge |
| R4 | **Style variance** — color furnished vs B&W CAD | High | Stratified splits; style-aware augmentation |
| R5 | **Mixed units** — scale calibration errors | High | OCR dimension parsing + door-width prior (0.9m / 3ft) |
| R6 | **No splits** — cannot report valid metrics | High | Create splits before any training run |
| R7 | **Opaque filenames** — annotation workflow friction | Medium | Build `metadata/{id}.json` with source hash + review status |
| R8 | **PDF confusion** — wrong asset type in same folder | Medium | Move PDFs to `data/interior_pdfs/` in new pipeline (don't modify `data/` now) |
| R9 | **JFIF format** — tooling compatibility | Low | Normalize to JPG on ingest |
| R10 | **3-file gdrive overlap** — potential double-counting | Low | Maintain global hash registry across `dataset/` |
| R11 | **Embedded text not labels** — OCR errors propagate to scale | Medium | Validate OCR against door-width prior |
| R12 | **No negative samples** — non-floor-plan images absent | Low | Add rejection class in production ingest |

---

## 12. Comparison with IMPROVED_MODEL_1 Design Expectations

| Design expectation (`FOLDER_STRUCTURE.md`) | Current `data/` status |
|---------------------------------------------|------------------------|
| `dataset/raw/` | Not created — use deduped `data/` root as source |
| `dataset/labels/train/` | **Missing** |
| `dataset/splits/` | **Missing** |
| `configs/dataset.yaml` | **Missing** |
| YOLO-seg labels | **Missing** |
| Train/val/test split | **Missing** |

---

## 13. Action Items (Read-Only Recommendations)

These actions should be performed in `IMPROVED_MODEL_1/dataset/` — **not by modifying `data/`**:

1. **Ingest script:** Copy 315 unique images (MD5 dedup) from `data/` root → `dataset/raw/`
2. **Skip `data/Era/`** entirely
3. **Normalize formats:** JFIF/GIF → JPG
4. **Quarantine PDFs:** Reference separately for interior track
5. **Create split manifest:** 221 train / 63 val / 31 test (70/20/10 of 315)
6. **Bootstrap labels:** Parse `model_2.svg` for first YOLO labels
7. **Annotate 30-plan seed set** in CVAT (Wall, Door, Window, Room)
8. **Register hashes** to prevent overlap with `gdrive_dataset/images_raw/`

---

## 14. Appendix — Scan Methodology

| Step | Tool | Details |
|------|------|---------|
| Recursive file enumeration | PowerShell + Python `pathlib` | All 570 files |
| Extension counting | Group-by suffix | Case-insensitive |
| MD5 deduplication | `hashlib.md5(full file bytes)` | Per-image uniqueness |
| Dimension extraction | JPEG SOF marker parser | 315/315 success |
| Color vs B&W | PIL + numpy chroma on 64×64 resize | Heuristic classification |
| Visual sampling | Manual review of 6 representative images | Content type confirmation |
| Cross-dataset hash compare | MD5 against `gdrive_dataset/`, `latest_interior/` | 3 overlaps found |
| Annotation detection | Extension + directory convention scan | Zero annotation files |

---

## 15. Appendix — Key Paths

| Resource | Path |
|----------|------|
| Audited dataset | `D:\HCI_interor\IMPROVED_MODEL_1\data\` |
| Duplicate subfolder | `D:\HCI_interor\IMPROVED_MODEL_1\data\Era\` |
| Related gdrive images | `D:\HCI_interor\gdrive_dataset\images_raw\` |
| CubiCasa SVG (external) | `D:\HCI_interor\latest_interior\latest_interior\model_2.svg` |
| Target ingest location | `D:\HCI_interor\IMPROVED_MODEL_1\dataset\raw\` (to be created) |

---

*End of Dataset Audit — read-only analysis, no files modified.*
