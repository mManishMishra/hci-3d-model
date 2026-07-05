# Architecture Analysis — Historical Reference

**Project:** IMPROVED_MODEL_1  
**Status:** **SUPERSEDED**  
**Date:** 2026-06-19

---

## Current Authority

This document is a **historical Phase 1 analysis**. The active system design is:

| Document | Scope |
|----------|-------|
| [HLD.md](./HLD.md) v2 | YOLO11 segmentation training architecture |
| [LLD.md](./LLD.md) v2 | Training module interfaces |
| [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) | Annotation authority |

---

## What Changed

The original architecture analysis described a multi-layer floor-plan processing platform. The **current milestone** is narrower:

```
Images → CVAT annotation → YOLO export → YOLO11 train → evaluate vs legacy
```

---

## Key Decisions (Current Phase)

1. **Three classes only** — wall, door, window
2. **Human labels** — not mock auto-label
3. **YOLO11** — not YOLOv8
4. **Proper val split** — not train=val=test
5. **Beat legacy first** — before any scope expansion

---

## Deferred Concepts

Any multi-stage pipeline concepts from the original analysis are **deferred** until structural segmentation mAP beats `web_file` / `web2`.

Stub modules in `src/` (graph, topology, schema, adapter, pipeline) reflect the old analysis — they are not part of the current training milestone.

---

## For New Engineers

Start here instead:

1. [docs/README.md](./README.md) — documentation index
2. [HLD.md](./HLD.md) — system overview
3. [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) — how to annotate
4. [ANNOTATION_EXECUTION_PLAN.md](./ANNOTATION_EXECUTION_PLAN.md) — what to do now

---

*Preserved for history. Do not use for current system design.*
