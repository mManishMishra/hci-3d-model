# Annotation Execution Plan — Prototype 11-Class Batch

**Version:** 1.0  
**Date:** 2026-06-11  
**Batch:** `data/prototype_11_batch/` (25 images)  
**Taxonomy:** `data/prototype_11_classes.yaml`  
**Status:** Annotation-ready — no training

---

## 1. Batch summary

| Metric | Value |
|--------|------:|
| Images selected | 25 |
| Source (read-only) | `dataset_clean/images/` |
| Batch location | `data/prototype_11_batch/images/` |
| Manifest | `data/prototype_11_batch/manifest.csv` |
| Selection script | `scripts/prepare_prototype_11_batch.py` |

### Style mix

| Style | Count | Purpose |
|-------|------:|---------|
| Line drawing (B&W CAD) | 8 | Clean structural + room polygons |
| Furnished / color | 17 | Symbol bboxes (bed, wc, sink, stove) |

### Quality metrics (batch average)

| Metric | Value |
|--------|------:|
| Mean sharpness (Laplacian var) | 5,647 |
| Min sharpness | 2,662 |
| All images ≥ minimum class support | ✅ 25 / 25 |
| Full 11-class symbol coverage | ✅ 25 / 25 |

---

## 2. Minimum support verification

Every selected image satisfies **required** classes:

| Required class | Images | Percent |
|----------------|-------:|--------:|
| wall | 25 | 100% |
| door | 25 | 100% |
| window | 25 | 100% |
| bedroom | 25 | 100% |
| kitchen | 25 | 100% |
| bathroom | 25 | 100% |

**Verification:** automated filter in `prepare_prototype_11_batch.py` + manifest columns `has_wall` … `has_bathroom` all `True`.

---

## 3. Class coverage matrix (batch)

| Class | Proto ID | Type | Images | Percent | Batch support |
|-------|---------:|------|-------:|--------:|---------------|
| wall | 0 | polygon | 25 | 100% | ✅ Universal |
| door | 1 | polygon | 25 | 100% | ✅ Universal |
| window | 2 | polygon | 25 | 100% | ✅ Universal |
| bedroom | 3 | polygon | 25 | 100% | ✅ Universal |
| living_room | 4 | polygon | 25 | 100% | ✅ Universal |
| kitchen | 5 | polygon | 25 | 100% | ✅ Universal |
| bathroom | 6 | polygon | 25 | 100% | ✅ Universal |
| bed | 7 | bbox | 25 | 100% | ✅ All batches |
| wc | 8 | bbox | 25 | 100% | ✅ All batches |
| sink | 9 | bbox | 25 | 100% | ✅ All batches |
| stove | 10 | bbox | 25 | 100% | ✅ All batches |

This batch was **ranked to maximize 11-class annotation value** — all images include furniture/fixture symbols per metadata and visual scoring.

---

## 4. Ranked image list

Annotate in rank order (highest value first):

| Rank | Filename | Style | Size | Sharpness | Score | Notes |
|-----:|----------|-------|------|----------:|------:|-------|
| 1 | `94da19bc-7654-43eb-9ba6-ae16efcbf547.jpg` | furnished_color | 650×929 | 4543 | 192.3 | full symbols |
| 2 | `e6796a33-6522-4140-8a7f-3aad46258b23.jpg` | furnished_color | 564×828 | 6160 | 191.2 | full symbols |
| 3 | `244a80fe000e5b8728c17211b2b7525d.jpg` | furnished_color | 735×607 | 6504 | 191.0 | full symbols |
| 4 | `6ba1d00d-4ec7-4123-996b-50fe3a14af79.jpg` | furnished_color | 500×877 | 17925 | 191.0 | full symbols; highest sharpness |
| 5 | `bcdae71e-cca6-46fb-ac11-add668ccb2dd.jpg` | furnished_color | 600×677 | 5131 | 190.7 | full symbols |
| 6 | `ccc951d1-7ce8-4546-ba57-99423b65202b.jpg` | line_drawing | 688×1257 | 5719 | 190.6 | full symbols; B&W |
| 7 | `b2a1a7e3abbe457cce92ac490428bafa.jpg` | line_drawing | 564×1993 | 4829 | 189.6 | full symbols; B&W |
| 8 | `fee59751-e33c-4787-9cf6-e16bcfac73c7.jpg` | line_drawing | 686×1188 | 4787 | 188.2 | full symbols; B&W |
| 9 | `358ffd35-b79e-46c1-934c-1ce9543958f2.jpg` | furnished_color | 640×903 | 6173 | 186.5 | full symbols |
| 10 | `fc915e1bc20c93897f96769b243893d2.jpg` | furnished_color | 533×1031 | 5326 | 185.4 | full symbols |
| 11 | `628d81db0bbddc6884c25a85ddd7e278.jpg` | furnished_color | 550×956 | 5505 | 185.0 | full symbols |
| 12 | `8fba8948-8b12-4fa9-8601-1224b694c107.jpg` | furnished_color | 564×772 | 4065 | 184.8 | full symbols |
| 13 | `8c6c7571c8fa3d65b33b60611626d13a.jpg` | line_drawing | 564×740 | 5588 | 184.5 | full symbols; B&W |
| 14 | `6549ac644ce535a6039b8b8bfdc68f6e.jpg` | furnished_color | 674×900 | 5987 | 183.2 | full symbols |
| 15 | `8403e0d1-923a-4474-b7db-3ad8acf0863a.jpg` | furnished_color | 1080×935 | 2900 | 182.2 | full symbols |
| 16 | `8906018545e276d2e21e5220c62074f1.jpg` | line_drawing | 736×941 | 4594 | 181.8 | full symbols; B&W |
| 17 | `f9312d16-1639-4a4e-b8f5-dceb5b0a43e8.jpg` | furnished_color | 638×688 | 3637 | 181.3 | full symbols |
| 18 | `65fce43ecf1817bc941558229757c178.jpg` | furnished_color | 736×1026 | 2958 | 180.5 | full symbols |
| 19 | `714aced82de7341fa2677af01c144ec9.jpg` | furnished_color | 735×1048 | 2791 | 179.2 | full symbols |
| 20 | `d34f12f415f2febef838494c8bbc7472.jpg` | line_drawing | 735×776 | 4345 | 179.2 | full symbols; B&W |
| 21 | `34e2afcc-abab-450e-8c36-61250c881347.jpg` | furnished_color | 550×617 | 9364 | 178.1 | full symbols |
| 22 | `69a35f1cab485159de27a6085a5a9813.jpg` | furnished_color | 564×582 | 5581 | 178.0 | full symbols |
| 23 | `0b79a51a-bede-49d3-b746-44351f4fd1ba.jpg` | line_drawing | 1021×1280 | 2662 | 177.7 | full symbols; B&W |
| 24 | `2a0e67cffb7acbf83547afdac272caa5.jpg` | line_drawing | 563×768 | 5236 | 177.5 | full symbols; B&W |
| 25 | `b92184c9a460e92fd303799fa50f750b.jpg` | furnished_color | 563×471 | 5210 | 175.3 | full symbols |

**Ranking formula:** CSV selection score + sharpness + edge clarity + symbol coverage + resolution sweet-spot − blur/artifact penalty.

---

## 5. Estimated annotation time

Per `docs/PROTOTYPE_11_CLASS_PLAN.md` — mixed polygon + bbox, ~32 min/image average.

| Phase | Scope | Time |
|-------|-------|-----:|
| Polygon pass (classes 0–6) | 25 images | ~10.4 h |
| Bbox pass (classes 7–10) | 25 images (symbols present) | ~4.2 h |
| Export + file validation | — | ~1.0 h |
| QC review (20% sample + all rank 1–5) | 10 images | ~2.7 h |
| **Total** | **25 images** | **~13.3 h base** |
| **With 30% revision buffer** | | **~17.3 h** |

| Team | Calendar |
|------|----------|
| 1 annotator | 2.2 working days |
| 2 annotators (split 13/12) | 1.2 working days + reviewer |

### Suggested schedule

| Day | Task | Images |
|-----|------|-------:|
| 1 AM | CVAT setup + polygon pass | Rank 1–10 |
| 1 PM | Polygon pass | Rank 11–20 |
| 2 AM | Polygon pass + bbox pass | Rank 21–25 |
| 2 PM | Bbox pass all + export | All |
| 3 | QC + revision | Val sample (5 held-out — see §7) |

---

## 6. CVAT setup instructions

### 6.1 Create project

1. Open CVAT → **Projects** → **Create new project**
2. Name: `IMPROVED_MODEL_1_Prototype11_Batch01`
3. Add labels from table below (enable **any** shape where noted)

| Label | Proto ID | Shape | Color |
|-------|---------:|-------|-------|
| wall | 0 | Polygon | `#FF0000` |
| door | 1 | Polygon | `#00CC00` |
| window | 2 | Polygon | `#0066FF` |
| bedroom | 3 | Polygon | `#FFE066` |
| living_room | 4 | Polygon | `#66CCFF` |
| kitchen | 5 | Polygon | `#FF9999` |
| bathroom | 6 | Polygon | `#66CCCC` |
| bed | 7 | Rectangle | `#8B4513` |
| wc | 8 | Rectangle | `#E0E0E0` |
| sink | 9 | Rectangle | `#5F9EA0` |
| stove | 10 | Rectangle | `#FF4500` |

### 6.2 Create task

1. **Create task** → upload all 25 images from `data/prototype_11_batch/images/`
2. Sort by filename or use manifest rank as job order
3. Enable **Attributes** (optional): `style` = line_drawing | furnished_color

### 6.3 Annotation order per image

1. Polygons: wall → door → window → bedroom → living_room → kitchen → bathroom
2. Rectangles: bed → wc → sink → stove (skip if symbol genuinely absent — none expected in this batch)
3. Save and mark complete

### 6.4 Export

| Export | Format | Output folder |
|--------|--------|---------------|
| Segmentation | YOLO 1.1 | `data/prototype_11_batch/labels/seg/` |
| Detection | YOLO 1.1 | `data/prototype_11_batch/labels/det/` |

Remap exported class names to prototype IDs 0–10 per `data/prototype_11_classes.yaml`.

### 6.5 Train/val split (after annotation)

| Split | Ranks | Count |
|-------|-------|------:|
| **Train** | 1–20 | 20 |
| **Val** | 21–25 | 5 |

Create symlinks or copy into `labels/seg/train`, `labels/seg/val`, `labels/det/train`, `labels/det/val` — do not alter `dataset_clean/`.

---

## 7. QA checklist

### Pre-annotation

- [ ] All 25 images open without corruption
- [ ] CVAT labels match `prototype_11_classes.yaml` (11 labels, correct colors)
- [ ] Annotators read `docs/ANNOTATION_GUIDELINES.md` v1.1
- [ ] `wc` vs `bathroom` distinction understood

### During annotation

- [ ] Every image has wall, door, window polygons
- [ ] Every image has bedroom, kitchen, bathroom room polygons
- [ ] living_room polygon present where labeled or inferable
- [ ] Door/window not confused (spot-check ranks 1, 6, 13)
- [ ] Symbol bboxes tight — no full-room boxes for wc/sink/stove
- [ ] No title block / dimension text annotated

### Post-export

- [ ] 25 seg label files in train+val folders
- [ ] 25 det label files (symbols present in all batch images)
- [ ] Class IDs 0–6 in seg; 7–10 in det (remapped if CVAT uses names)
- [ ] All coordinates normalized ∈ [0, 1]
- [ ] Val ranks 21–25 reviewed by second annotator
- [ ] Manifest updated with `annotated=true` and `annotator` columns (manual)

### Sign-off gate (before any training)

- [ ] QC pass rate ≥ 95% on val split
- [ ] Zero missing required classes on val set
- [ ] Export validation script passes
- [ ] BIM reviewer spot-checks 3 annotated plans

---

## 8. Selection criteria applied

| Criterion | How enforced |
|-----------|--------------|
| Clear floor plans | Sharpness threshold; penalized blur < 50 Laplacian var |
| Visible walls, doors, windows | CSV `has_*` flags + edge density ≥ 0.008 |
| Visible room labels | bedroom, kitchen, bathroom required in metadata |
| Visible fixtures | bed, toilet→wc, sink, stove required in metadata |
| Minimal blur | Sharpness scoring; rank 23 lowest at 2662 still acceptable |
| Minimal rendering artifacts | Prefer line_drawing + high-quality furnished; exclude color_rendered-only |

---

## 9. Related files

| File | Purpose |
|------|---------|
| `data/prototype_11_batch/manifest.csv` | Ranked list + class flags |
| `data/prototype_11_batch/selection.json` | Selection summary JSON |
| `data/prototype_11_classes.yaml` | 11-class taxonomy |
| `docs/PROTOTYPE_11_CLASS_PLAN.md` | Training plan (post-annotation) |
| `docs/ANNOTATION_GUIDELINES.md` | Per-class rules |
| `scripts/prepare_prototype_11_batch.py` | Reproducible selection |

---

## 10. Regenerate batch (optional)

```powershell
cd D:\HCI_interor\IMPROVED_MODEL_1
python scripts/prepare_prototype_11_batch.py
```

Copies from `dataset_clean/images/` → `data/prototype_11_batch/images/` (source remains unchanged).
