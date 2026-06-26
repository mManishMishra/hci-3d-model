# Class Support Analysis — Training Reference

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19

---

## System Goal

Use corpus analysis to prioritize **wall, door, window** annotation and training — the classes that must beat legacy `web_file` / `web2`.

---

## Active Training Scope

**Train only classes 0–2.** This analysis informed batch selection but extended class recommendations are **deferred**.

| Class | Train now? |
|-------|------------|
| wall | ✅ Yes |
| door | ✅ Yes |
| window | ✅ Yes |
| rooms, furniture, fixtures | ❌ Deferred |

---

## Corpus Findings (Summary)

Analysis of ~315 unique floor-plan images (`data/analysis_all_images.csv`):

| Finding | Implication for training |
|---------|--------------------------|
| ~75% of images show wall/door/window ink | Strong support for 3-class structural training |
| Mix of B&W CAD and furnished plans | Stratify val set across styles |
| Resolution mostly < 1 MP | Use `imgsz=1024` |
| Furniture present in ~28% of batch | Ignore for current milestone — do not annotate |
| Sharpness varies | Prefer crisp B&W plans for first 25-image batch |

---

## Batch Selection Rationale

`prototype_11_batch/` (25 images) was selected for:

- Visible structural classes (wall, door, window) in every image
- Mix of complexity levels (simple → complex by rank)
- ~28% furnished (for visual diversity — annotate structure only)

**Annotation scope:** classes 0–2 only, regardless of furnished content.

---

## Expected Performance (Structural Only)

| Metric | Target (25 train / 5 val) |
|--------|---------------------------|
| wall mAP50 | 0.70–0.85 |
| door mAP50 | 0.65–0.80 |
| window mAP50 | 0.65–0.80 |
| vs legacy delta | Positive on ≥ 2 of 3 classes |

*Estimates assume human-verified labels per canonical rulebook.*

---

## Deferred Analysis

The original report recommended 11–28 class training for extended demonstration value. That recommendation is **superseded** by the current milestone:

> Beat legacy on structural segmentation first. Expand classes only after validated baseline.

Full statistical tables remain in `data/class_support_analysis.json` and `data/class_frequency.json` for future reference.

---

## Recommendations (Current Phase)

1. **Annotate** `prototype_11_batch/` with classes 0–2 only
2. **Train** YOLO11n-seg at imgsz=1024
3. **Compare** mAP50 vs `web_file` on same 5 val images
4. **Expand** to 50 images if structural mAP below target
5. **Do not** annotate rooms/furniture until step 3 passes

---

*Class support analysis v2 — structural training scope only.*
