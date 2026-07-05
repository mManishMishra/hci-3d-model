# Prototype Annotation Guide — 7-Class

**Batch:** `data/prototype_7_batch/`  
**Rulebook:** [CANONICAL_ANNOTATION_RULEBOOK.md](./CANONICAL_ANNOTATION_RULEBOOK.md)

---

## CVAT

- Project: `IMPROVED_MODEL_1_7Class_Seg`
- Tool: Polygon only
- Classes 0–6 (see rulebook for colors)

---

## Annotation order

1. **wall** — full thickness, split at corners, gap at openings  
2. **door** — opening symbol only  
3. **window** — opening symbol only  
4. **bedroom**, **living_room**, **kitchen**, **bathroom** — interior floor boundaries  

---

## Export pipeline

```bash
python scripts/export_cvat_to_yolo.py <cvat_export_dir> --validate
python scripts/check_dataset_integrity.py
```

---

## Training (after labels)

```bash
python scripts/train.py
```

---

*7-class prototype guide.*
