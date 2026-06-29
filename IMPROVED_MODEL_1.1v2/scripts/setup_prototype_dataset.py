#!/usr/bin/env python3
"""Select 10 fast-annotate images and prepare prototype YOLO dataset folders."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH = PROJECT_ROOT / "data" / "annotation_batch_01"
ANALYSIS = PROJECT_ROOT / "data" / "analysis_all_images.csv"
OUT = PROJECT_ROOT / "data" / "prototype_dataset"
PROTOTYPE_LIST = PROJECT_ROOT / "data" / "prototype_10_images.txt"

FURNITURE_CLASSES = {
    "bed", "sofa", "stove", "wardrobe", "chair", "table", "sink", "toilet"
}


def main() -> None:
    batch_files = {p.name for p in BATCH.glob("*.jpg")}
    rows: list[dict] = []

    with ANALYSIS.open(encoding="utf-8") as f:
        for record in csv.DictReader(f):
            if record["filename"] not in batch_files:
                continue
            w, h = int(record["width"]), int(record["height"])
            mp = w * h / 1e6
            furn = record["has_furniture"] == "True"
            style = record["style"]
            vc = record["visible_classes"].split(";")
            furn_classes = sum(1 for c in vc if c in FURNITURE_CLASSES)
            fast = 0.0
            fast += 30 if style == "line_drawing" else (5 if style == "color_rendered" else 0)
            fast += 25 if not furn else 0
            fast += max(0, 20 - mp * 15)
            fast += max(0, 15 - furn_classes * 2)
            fast += 10 if min(w, h) >= 500 else 0
            if min(w, h) > 0 and max(w, h) / min(w, h) > 1.8:
                fast -= 15
            fast += 5 if {"door", "window", "wall"}.issubset(set(vc)) else 0
            rows.append({
                "filename": record["filename"],
                "w": w,
                "h": h,
                "mp": mp,
                "style": style,
                "furn": furn,
                "furn_classes": furn_classes,
                "fast_score": fast,
            })

    by_name = {r["filename"]: r for r in rows}

    # Curated for 10-hour prototype: B&W line drawings, clear symbols, ~15-25 min each.
    curated = [
        "22177c44-e3e1-4d32-8f5f-449416c7f28f.jpg",  # 3-room suite — simplest
        "ae4cdbb8-e2b5-4e03-82e5-26c97c0abeb6.jpg",  # structural, no furniture clutter
        "852f2a15-23c8-45aa-93f4-e65267a48d12.jpg",  # compact landscape
        "577f8173-8c69-4ac6-a63c-d9ffdcbc3e43.jpg",  # medium vertical
        "ebb42e5a-9488-49bd-9b26-ffa78743e87f.jpg",
        "938c6fc1-381d-4e9b-83d7-0d5e1aa709e2.jpg",
        "72aab0a0-c546-4e47-addd-abd510c5bf79.jpg",
        "4a17677b-cff0-4922-a564-4768195fe5a9.jpg",
        "ef320344-ea55-4976-9b95-0f1e1dc643ad.jpg",
        "009b1b7a-ff37-4d1a-9d6c-47b8bd4862b2.jpg",  # 1 larger CAD plan for diversity
    ]
    missing = [n for n in curated if n not in by_name]
    if missing:
        raise FileNotFoundError(f"Curated images not in batch: {missing}")

    selected = [by_name[n] for n in curated]
    names = curated
    PROTOTYPE_LIST.write_text("\n".join(names), encoding="utf-8")

    # Val: smallest + most compact for quick iteration checks
    val_names = {
        "852f2a15-23c8-45aa-93f4-e65267a48d12.jpg",
        "22177c44-e3e1-4d32-8f5f-449416c7f28f.jpg",
    }

    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    for record in selected:
        split = "val" if record["filename"] in val_names else "train"
        shutil.copy2(BATCH / record["filename"], OUT / f"images/{split}" / record["filename"])

    for split in ("train", "val"):
        (OUT / "labels" / split / "README.txt").write_text(
            "Place YOLO-seg label files here after CVAT export.\n"
            f"One .txt per image in images/{split}/\n"
            "Format: class_id x1 y1 x2 y2 ... (normalized 0-1 polygon)\n",
            encoding="utf-8",
        )

    manifest = OUT / "prototype_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "filename", "split", "width", "height", "megapixels",
            "style", "fast_score", "notes",
        ])
        for record in selected:
            split = "val" if record["filename"] in val_names else "train"
            notes = (
                "Smallest plan — annotate first"
                if record["mp"] < 0.5
                else "B&W line drawing — walls/doors/windows only"
            )
            writer.writerow([
                record["filename"], split, record["w"], record["h"],
                f"{record['mp']:.3f}", record["style"],
                f"{record['fast_score']:.1f}", notes,
            ])

    stats = {
        "selected": names,
        "train": [r["filename"] for r in selected if r["filename"] not in val_names],
        "val": sorted(val_names),
    }
    (OUT / "selection.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
