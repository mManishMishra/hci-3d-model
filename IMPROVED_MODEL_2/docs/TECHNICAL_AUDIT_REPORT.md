# Technical Audit Report — Legacy Training Systems

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19

---

## System Goal

Document legacy `web_file` and `web2` training weaknesses and define what IMPROVED_MODEL_1 must do better.

---

## Legacy Systems Summary

### `web_file` (runnable baseline)

| Component | Status |
|-----------|--------|
| FastAPI trainer UI | ✅ Works |
| Ultralytics YOLOv8-seg | ✅ Works |
| `contour_to_yolo_seg()` | ✅ Reusable format |
| Train + finetune workers | ✅ Works if labels exist |
| Auto-label on ingest | ❌ **Mock detector returns empty** |
| Dataset labels in repo | ❌ None |
| Val split | ❌ **train=val=test** |
| Classes | 17 (incl. Room loops) |

### `web2` (incomplete fork)

| Component | Status |
|-----------|--------|
| Extended `server.py` | Subset finetune, extra APIs |
| Runnable standalone | ❌ Missing `logic/`, `config/` |
| Training improvements | Subset finetune only |
| Same core weaknesses | Mock detector, 17-class, bad split |

---

## Legacy Training Flow

```
Upload image → mock auto-label (empty) → manual correction UI → train YOLOv8-seg
```

**Problem:** Auto-label produces zero instances. Training only works if human manually corrects in the web UI — no CVAT workflow, no QC, no reproducible pipeline.

---

## Legacy Weaknesses → IMPROVED_MODEL_1 Fixes

| Weakness | Legacy | IMPROVED_MODEL_1 |
|----------|--------|------------------|
| Labels | Mock / empty auto-label | CVAT human polygons |
| Classes | 17 (Room confusion) | 3 structural |
| Model | YOLOv8n-seg | YOLO11n-seg |
| imgsz | 640 default | 1024 |
| Val split | train=val=test | 20/5 proper split |
| Wall definition | Inconsistent | Full thickness, split at corners |
| QC | None | Val review + validation script |
| Reproducibility | Web UI only | CLI `scripts/train.py` |
| Baseline comparison | None | Side-by-side mAP |

---

## Reusable from Legacy (Read-Only)

| Asset | Path | Use |
|-------|------|-----|
| YOLO-seg line format | `web_file/web/auto_label.py` | `contour_to_yolo_seg()` pattern |
| Train worker callbacks | `web_file/web/server.py` | Port to `scripts/train.py` |
| Correction UI patterns | `web_file/web/index.html` | Reference for future tooling |

**Do not modify** legacy projects.

---

## IMPROVED_MODEL_1 Implementation Gap

| Component | Status |
|-----------|--------|
| Annotation rulebook | ✅ Complete |
| Images staged | ✅ 25-image batch |
| Labels | ❌ 0 exported |
| `scripts/train.py` | ❌ Not implemented |
| `ultralytics` dependency | ❌ Not in requirements |
| Baseline eval | ❌ Not implemented |

---

## Recommendation

1. Port train-worker pattern from `web_file` into `scripts/train.py`
2. Use 3-class taxonomy — not legacy 17-class
3. Never replicate train=val=test split
4. Compare IMPROVED_MODEL_1 val mAP against legacy trained on **same 20 train images**

---

## Out of Scope for This Audit

- Downstream processing beyond mask prediction
- Integration with non-training reference projects
- Full-platform architecture comparisons

---

*Technical audit v2 — focused on segmentation training vs legacy.*
