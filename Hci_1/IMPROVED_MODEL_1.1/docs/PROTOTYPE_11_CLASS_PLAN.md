# Prototype 11-Class Plan — DEFERRED

**Project:** IMPROVED_MODEL_1  
**Status:** **DEFERRED — NOT ACTIVE**  
**Date:** 2026-06-19

---

## Current Milestone Scope

The active training milestone uses **3 classes only:**

| ID | Class |
|----|-------|
| 0 | wall |
| 1 | door |
| 2 | window |

See [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md).

---

## What This Document Originally Described

An 11-class prototype plan (7 segmentation + 4 detection) covering rooms and fixture symbols:

| IDs | Classes | Type |
|-----|---------|------|
| 0–2 | wall, door, window | Segmentation |
| 3–6 | bedroom, living_room, kitchen, bathroom | Segmentation |
| 7–10 | bed, wc, sink, stove | Detection (bbox) |

Config reference: `data/prototype_11_classes.yaml` (dataset file — not modified by this doc update)

---

## Why Deferred

1. **Current goal** is to beat legacy on structural segmentation first
2. Mixed seg+det adds annotation complexity without improving wall/door/window mAP
3. Legacy weakness is structural classes — not room labels
4. 25-image batch should be annotated with classes 0–2 only

---

## When to Revisit

Reactivate this plan only when:

- [ ] YOLO11 structural mAP (classes 0–2) beats `web_file` on val set
- [ ] 50+ images have validated structural labels
- [ ] Team explicitly expands scope to room/symbol classes

---

## Active Batch Usage

The 25 images in `data/prototype_11_batch/` remain the active annotation batch — but annotate **only classes 0–2**, not all 11.

Execution plan: [ANNOTATION_EXECUTION_PLAN.md](./ANNOTATION_EXECUTION_PLAN.md)

---

*This plan is preserved for future reference. It is not part of the current YOLO11 segmentation milestone.*
