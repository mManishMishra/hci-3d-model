# CVAT Overview — For Stakeholders & Team

**Project:** IMPROVED_MODEL_1  
**Audience:** Senior review, project managers, annotators, developers  
**Last updated:** June 2026  

---

## 1. What is CVAT?

**CVAT** (Computer Vision Annotation Tool) is an open-source web application used to create high-quality training data for AI vision models.

In simple terms:

> CVAT is a **professional labeling workspace** where a human draws shapes (polygons, boxes, etc.) on images and assigns a **class name** to each shape — for example *wall*, *kitchen*, *door*. Those labels are exported and used to **train** models such as YOLO.

| Item | Detail |
|------|--------|
| **Full name** | Computer Vision Annotation Tool |
| **Type** | Web-based annotation platform |
| **License** | Open source (Apache 2.0) |
| **Maintainer** | OpenCV / CVAT.ai community |
| **Official site** | https://www.cvat.ai |
| **Documentation** | https://docs.cvat.ai |
| **Typical deployment** | Docker on local server or cloud |

CVAT is widely used in industry for object detection, segmentation, and video annotation. It is **not** a training tool by itself — it produces the **dataset labels** that training scripts (YOLO, etc.) consume.

---

## 2. Why we use CVAT in IMPROVED_MODEL_1

Our legacy Floor Plan Trainer (`web_file` / `web2`) has a **Correct Labels** tab where users draw regions on floor plans. That UI is useful for review, but it has limits for **training-quality** labels:

| Limitation (legacy Correct page) | CVAT advantage |
|----------------------------------|----------------|
| Manual draw is **rectangle only** | **Free polygon** tool — follow wall lines accurately |
| Labels often start from **mock auto-label** | **Human-first** ground truth |
| Many UI room types collapse to one `Room` class in training | Each class in CVAT = **real YOLO training class** |
| Weak train/validation discipline | Export → validate → train pipeline |
| Hard to scale QC across annotators | Reviewer roles, issue tracking, standards |

**CVAT does not replace our trainer GUI forever.** It replaces **low-quality annotation** for the new model. After training, the same Floor Plan Trainer UI can be used for **Test Model** and **Train / Update Model** with the new weights.

---

## 3. How CVAT fits our project workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  IMPROVED_MODEL_1 — End-to-end pipeline                         │
└─────────────────────────────────────────────────────────────────┘

  Floor plan images (prototype_7_batch)
           │
           ▼
  ┌─────────────────┐
  │  CVAT           │  Human draws polygons per class
  │  (annotation)   │  Project: IMPROVED_MODEL_1_7Class_Seg
  └────────┬────────┘
           │ Export: YOLO 1.1 Segmentation
           ▼
  ┌─────────────────┐
  │ export_cvat_    │  Remap class IDs → locked 0–6
  │ to_yolo.py      │
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ validate_labels │  QC gate — reject bad labels
  │ .py             │
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ train.py        │  YOLO11n-seg @ 1024px
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ evaluate.py     │  Compare vs legacy web_file model
  └────────┬────────┘
           ▼
  Floor Plan Trainer GUI — Test Model tab (future integration)
```

---

## 4. Our CVAT configuration (current)

| Setting | Value |
|---------|--------|
| **CVAT project name** | `IMPROVED_MODEL_1_7Class_Seg` |
| **Task type** | Instance **segmentation** (polygons) |
| **Active classes (Phase 1)** | 7 — see table below |
| **Image batch** | `data/prototype_7_batch/` (25 images) |
| **Config source** | `data/prototype_7_classes.yaml` |
| **Annotation rules** | `docs/CANONICAL_ANNOTATION_RULEBOOK.md` |

### Active classes (Phase 1 — locked)

| ID | Class name | What to annotate |
|----|------------|------------------|
| 0 | wall | Wall thickness as closed polygon |
| 1 | door | Door opening symbol |
| 2 | window | Window opening symbol |
| 3 | bedroom | Interior floor area |
| 4 | living_room | Interior floor area |
| 5 | kitchen | Interior floor area |
| 6 | bathroom | Interior floor area |

**Annotation order:** wall → door → window → bedroom → living_room → kitchen → bathroom

---

## 5. CVAT vs legacy Correct Labels — comparison

| Aspect | Legacy Correct Labels (web2) | CVAT |
|--------|------------------------------|------|
| **Purpose** | Quick fix inside trainer app | Professional dataset creation |
| **Shape tool** | Rectangle → 4-point polygon | True polygon (many vertices) |
| **Class list in UI** | 40+ options (room subtypes, MEP, etc.) | Matches **active training classes** |
| **What model learns today** | Many types collapse (e.g. all rooms → `Room`) | **What you label is what trains** |
| **Label validation** | Minimal | Script-based QC before training |
| **Best for** | Demo, quick edits, legacy 17-class model | **IMPROVED_MODEL_1** high-quality training |

### Senior requirement alignment

> *“User marks area as per the list — same should be used for model training.”*

- **Intent:** Dropdown type = training class = model prediction.  
- **Legacy gap:** UI shows Kitchen, Puja Room, etc., but training often saves only `Room`.  
- **CVAT fix:** Label `kitchen` in CVAT → export as class `kitchen` → model learns `kitchen`.  
- **Future:** Expand CVAT classes in phases to match the full Correct Labels list (→ 37-class taxonomy in `data/classes.yaml`).

---

## 6. Can CVAT be added to our GUI?

**Yes.** CVAT runs as a service; our Floor Plan Trainer can integrate it.

### Recommended integration (phased)

| Phase | Integration | User experience |
|-------|-------------|-----------------|
| **A (now)** | CVAT separate + manual export script | Annotator opens CVAT in browser |
| **B (next)** | **“Annotate in CVAT”** button in trainer GUI | Select image → open CVAT task → import labels back |
| **C (later)** | CVAT REST API in backend | Upload, sync classes, auto-import, trigger train from one app |

We do **not** need to rebuild CVAT inside Correct Labels. We **connect** our GUI to CVAT and to the same class list (`classes.yaml`).

---

## 7. Who uses CVAT and when

| Role | Action |
|------|--------|
| **Annotator** | Draw polygons in CVAT per rulebook |
| **Reviewer** | Check val-set images, reject/fix errors |
| **ML engineer** | Export, validate, train, evaluate |
| **Senior / PM** | Approve class phases (7 → expanded → 37) |

**Annotator quick steps:** See [PROTOTYPE_ANNOTATION_GUIDE.md](./PROTOTYPE_ANNOTATION_GUIDE.md)  
**Full execution plan:** See [ANNOTATION_EXECUTION_PLAN.md](./ANNOTATION_EXECUTION_PLAN.md)

---

## 8. Export and training commands (technical)

After annotation in CVAT:

1. CVAT → Menu → Export → **YOLO 1.1 segmentation**  
2. Run import + validation:

```bash
cd IMPROVED_MODEL_1
python scripts/export_cvat_to_yolo.py <path_to_cvat_export> --validate
python scripts/check_dataset_integrity.py
```

3. Train when labels pass QC:

```bash
python scripts/train.py
```

4. Evaluate vs legacy:

```bash
python scripts/evaluate.py
```

---

## 9. Phased class expansion (7 → 37)

CVAT class list will grow as the model matures. We do **not** annotate all 40+ Correct Labels types on day one.

| Phase | CVAT classes | Goal |
|-------|--------------|------|
| **1 (current)** | 7 core classes | First strong YOLO11 model; beat legacy |
| **2** | + column, stair | Structural extras |
| **3** | + dining_room, toilet, balcony, corridor, utility, etc. | Match more Correct Labels room types |
| **4** | + furniture classes | Furnished plans |
| **5** | + fixtures & appliances | Full 37-class production taxonomy |

Reference taxonomy: `data/classes.yaml`

---

## 10. FAQ

### Is CVAT a replacement for our Floor Plan Trainer app?

**No.** CVAT is for **creating labels**. Our trainer app remains for **training trigger, testing, and demos**. They work together.

### Is CVAT paid?

Open-source self-hosted version is **free**. CVAT.ai also offers hosted/enterprise options. We plan **self-hosted Docker** for data control.

### Do we still need the Correct Labels page?

For the **legacy 17-class model**, optionally yes. For **IMPROVED_MODEL_1**, primary annotation is CVAT. Correct page may later be used for quick review or retired for labeling.

### Why not annotate only in Correct Labels?

Rectangle-only editing and collapsed room classes limit model quality. CVAT provides the polygon precision and class honesty required to beat legacy.

### When can we test in the same UI as the screenshot?

After first `best.pt` is trained — plug weights into **Test Model** tab. Class dropdown grows as more classes are trained.

---

## 11. Related documents

| Document | Purpose |
|----------|---------|
| [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md) | Annotation rules (7-class) |
| [PROTOTYPE_ANNOTATION_GUIDE.md](./PROTOTYPE_ANNOTATION_GUIDE.md) | Annotator quick guide |
| [ANNOTATION_EXECUTION_PLAN.md](./ANNOTATION_EXECUTION_PLAN.md) | Step-by-step CVAT setup |
| [CLASS_TAXONOMY.md](./CLASS_TAXONOMY.md) | Class IDs and future 37-class map |
| [HLD.md](./HLD.md) | System high-level design |

---

## 12. External references

- CVAT official: https://www.cvat.ai  
- CVAT documentation: https://docs.cvat.ai  
- CVAT GitHub: https://github.com/cvat-ai/cvat  
- Ultralytics YOLO (our training framework): https://docs.ultralytics.com  

---

*This document explains CVAT for stakeholders. For annotation rules and class locks, always follow CANONICAL_ANNOTATION_RULEBOOK.md and prototype_7_classes.yaml.*
