# IMPROVED_MODEL_1 — Design Documentation Index

**Project:** AI Training Pipeline for Floor Plan → BIM Generation  
**Workspace:** `D:\HCI_interor\IMPROVED_MODEL_1`  
**Status:** Design phase — no implementation code yet  
**Date:** 2026-06-09

---

## Document Set

| # | Document | Description |
|---|----------|-------------|
| 1 | [TECHNICAL_AUDIT_REPORT.md](./TECHNICAL_AUDIT_REPORT.md) | Complete audit of all reference projects |
| 2 | [HLD.md](./HLD.md) | High-Level Design — system architecture |
| 3 | [LLD.md](./LLD.md) | Low-Level Design — modules, interfaces, data flows |
| 4 | [TECH_STACK.md](./TECH_STACK.md) | Recommended technology stack |
| 5 | [FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md) | Project directory layout |
| 6 | [DEVELOPMENT_ROADMAP.md](./DEVELOPMENT_ROADMAP.md) | 4-week phased delivery plan |
| 7 | [ARCHITECTURE_ANALYSIS.md](./ARCHITECTURE_ANALYSIS.md) | Prior Phase 1 deep-dive (reference) |

---

## Target Pipeline

```
Floor Plan Image
      ↓
Image Preprocessing
      ↓
Wall / Door / Window Detection  (YOLO)
      ↓
Building Graph Generation
      ↓
Topology Validation
      ↓
Structured BIM JSON  (BuildingAnalysis)
      ↓
IFC Generation  (IfcOpenShell)
      ↓
3D BIM Viewer
```

---

## Constraints

- **Do not modify** existing projects (`floorplan_ifc_ai`, `latest_interior`, `latest_interior_v1`, `web_file`, `gdrive_dataset`)
- Reference implementations are read-only inputs to this design
- IFC compiler from V3 is **referenced**, not rewritten in Phase 1
- No model training until pipeline infrastructure is complete

---

## Quick Reference — Reuse vs Replace

| Reuse from existing | Replace with new |
|---------------------|------------------|
| V3 `BuildingAnalysis` schema | Gemini extraction |
| V3 `ifc_properties.py` semantics | Mock detector/OCR |
| V3 `build_detailed_ifc()` (adapter) | LLM completeness heuristics |
| `web_file` 17-class taxonomy | Monolithic scripts |
| YOLO-seg label format | Train=val split |
| CubiCasa SVG parser (new, from `model_2.svg`) | In-memory training state |
