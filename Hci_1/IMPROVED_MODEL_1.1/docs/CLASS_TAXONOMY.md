# Class Taxonomy — 7-Class Active System

**Project:** IMPROVED_MODEL_1  
**Status:** **ACTIVE — LOCKED**  
**Config:** `data/prototype_7_classes.yaml`

---

## Active training classes (prototype IDs 0–6)

| ID | Name | Group | Annotation |
|----|------|-------|------------|
| 0 | wall | structural | Polygon |
| 1 | door | structural | Polygon |
| 2 | window | structural | Polygon |
| 3 | bedroom | rooms | Polygon |
| 4 | living_room | rooms | Polygon |
| 5 | kitchen | rooms | Polygon |
| 6 | bathroom | rooms | Polygon |

---

## Production ID map (future scale-up)

When merging into the full `data/classes.yaml` taxonomy (37 IDs), prototype IDs map to:

| Prototype | Production |
|----------:|-----------:|
| 0 | 0 (wall) |
| 1 | 1 (door) |
| 2 | 2 (window) |
| 3 | 5 (bedroom) |
| 4 | 7 (living_room) |
| 5 | 9 (kitchen) |
| 6 | 10 (bathroom) |

---

## Deferred (not in active training)

- 11-class mixed seg+det plan
- 37-class full taxonomy (`data/classes.yaml` — reference only)
- Symbol bbox classes (bed, wc, sink, stove)

---

## Legacy comparison

`web_file` uses 17 classes with `Room` (ID 3) as perimeter loops. IMPROVED_MODEL_1 uses **distinct room interior polygons** (IDs 3–6) separate from walls.

---

*7-class taxonomy locked for annotation and training.*
