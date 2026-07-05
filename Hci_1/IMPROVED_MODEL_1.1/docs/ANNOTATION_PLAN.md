# Annotation Plan

**Project:** IMPROVED_MODEL_1 — YOLO11 Segmentation Training  
**Version:** 2.0  
**Date:** 2026-06-19

---

## System Goal

Define annotation strategy for producing ground-truth YOLO segmentation labels that enable IMPROVED_MODEL_1 to outperform legacy `web_file` / `web2` on wall, door, and window detection.

---

## Annotation Philosophy

| Principle | Rationale |
|-----------|-----------|
| **Human-verified over auto-label** | Legacy mock detector returns empty labels |
| **Three classes only** | Avoid 17-class Room-loop confusion |
| **Full-thickness walls** | Not centerlines — matches visible geometry |
| **Split at corners** | One polygon per wall run |
| **Gap at openings** | Walls stop; door/window fill opening |
| **QC before train** | Val set 100% reviewed |

---

## Tooling

| Tool | Role |
|------|------|
| **CVAT** (Docker) | Primary annotation environment |
| `cursor_draft_annotator.py` | Draft helper only — not ground truth |
| `manifest.csv` | Train/val assignment by rank |

---

## Class Scope

### Active (annotate now)

| ID | Class | Type |
|----|-------|------|
| 0 | wall | Polygon — full thickness |
| 1 | door | Polygon — opening symbol |
| 2 | window | Polygon — opening symbol |

### Deferred (do not annotate for current milestone)

- Room polygons (bedroom, kitchen, etc.)
- Furniture/fixture bounding boxes
- Extended taxonomy (11-class, 37-class plans)

---

## Annotation Workflow

```
Select batch images
    → CVAT import
    → Annotate wall → door → window
    → Peer review (val set mandatory)
    → Export YOLO 1.1 seg
    → Validate class IDs + coordinates
    → Place in labels/{train,val}/
    → Train YOLO11
```

---

## Quality Control

### Per-image checks

- All visible walls traced (full thickness)
- Corners split correctly
- Openings have gaps in walls
- Doors include swing arcs where drawn
- No room perimeter loops labeled as walls
- No dimension lines labeled as walls

### Batch checks

- Val set (5 images): 100% reviewer sign-off
- Train set: 20% spot-check
- Export ID remap verified
- Pairing: every image has matching `.txt`

### Rejection criteria

- Centerline walls → reject and redo
- Merged corners → reject and split
- Wrong class ID → reject and remap
- Missing openings → reject and add gaps

---

## Dataset Phases

| Phase | Images | Classes | Goal |
|-------|-------:|---------|------|
| **A (current)** | 25 | 0–2 | First YOLO11 baseline |
| **B** | +25 (50 total) | 0–2 | Beat legacy mAP |
| **C** | 100+ | 0–2 | Production-quality structural model |
| **D (deferred)** | TBD | 3+ | Extended classes — only after Phase C |

---

## Export Specification

- Format: YOLO 1.1 instance segmentation
- One line per polygon instance
- Normalized coordinates [0, 1]
- Output: `labels/train/*.txt`, `labels/val/*.txt`

Authoritative details: [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md)

---

## Comparison vs Legacy Annotation

| Aspect | `web_file` | IMPROVED_MODEL_1 |
|--------|------------|------------------|
| Label source | Mock detector (empty) | CVAT human polygons |
| Wall definition | Inconsistent / Room loops | Full thickness, split at corners |
| Classes | 17 | 3 |
| QC | None | Val review mandatory |
| Export validation | None | Pre-train gate |

---

## Do Not Train Until

1. Phase A labels complete (25 images)
2. Validation passes (≥ 95% QC on val)
3. `dataset.yaml` created with train ≠ val

---

*Annotation plan v2 — structural segmentation training only.*
