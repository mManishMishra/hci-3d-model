#!/usr/bin/env python3
"""Analyze cleaned dataset class visibility and write frequency report."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_CSV = PROJECT_ROOT / "data" / "analysis_all_images.csv"
CLEAN_MANIFEST = PROJECT_ROOT / "dataset_clean" / "images"
OUTPUT_JSON = PROJECT_ROOT / "data" / "class_frequency.json"

TAXONOMY_GROUPS: dict[str, list[str]] = {
    "structural": ["wall", "door", "window", "column", "stair"],
    "rooms": [
        "bedroom",
        "master_bedroom",
        "living_room",
        "dining_room",
        "kitchen",
        "bathroom",
        "toilet",
        "balcony",
        "utility",
        "corridor",
    ],
    "furniture": [
        "bed",
        "wardrobe",
        "sofa",
        "chair",
        "dining_table",
        "coffee_table",
        "study_table",
        "tv_unit",
        "side_table",
        "dresser",
        "storage_unit",
        "cabinet",
    ],
    "fixtures": ["wc", "wash_basin", "shower", "bathtub", "sink"],
    "appliances": ["stove", "refrigerator", "washing_machine", "microwave", "chimney"],
}

# Map legacy analysis labels to taxonomy class names.
ANALYSIS_ALIASES: dict[str, str] = {
    "table": "dining_table",
    "toilet": "wc",
}

TRAIN_NOW_MIN_IMAGE_RATE = 0.95
TRAIN_NOW_STRUCTURAL = frozenset({"wall", "door", "window"})


@dataclass(frozen=True)
class ClassStats:
    name: str
    group: str
    images_with_class: int
    total_images: int
    image_rate: float
    train_phase: str
    yolo_id: int
    analysis_source: str | None


def all_classes() -> list[tuple[str, str]]:
    ordered: list[tuple[str, str]] = []
    for group, names in TAXONOMY_GROUPS.items():
        for name in names:
            ordered.append((group, name))
    return ordered


def assign_train_phase(name: str, image_rate: float, images_with_class: int) -> str:
    if name in TRAIN_NOW_STRUCTURAL:
        return "train_now"
    if image_rate >= TRAIN_NOW_MIN_IMAGE_RATE:
        return "train_now"
    return "train_later"


def analyze() -> dict:
    rows = list(csv.DictReader(ANALYSIS_CSV.open(encoding="utf-8")))
    total_images = len(rows)

    clean_count = len(list(CLEAN_MANIFEST.glob("*.jpg"))) if CLEAN_MANIFEST.is_dir() else 0

    presence: Counter[str] = Counter()
    raw_labels: Counter[str] = Counter()

    for row in rows:
        labels = row["visible_classes"].split(";")
        seen_in_image: set[str] = set()
        for label in labels:
            raw_labels[label] += 1
            mapped = ANALYSIS_ALIASES.get(label, label)
            seen_in_image.add(mapped)
        for cls in seen_in_image:
            presence[cls] += 1

    classes: list[dict] = []
    for yolo_id, (group, name) in enumerate(all_classes()):
        count = presence.get(name, 0)
        rate = count / total_images if total_images else 0.0
        source = None
        for raw, mapped in ANALYSIS_ALIASES.items():
            if mapped == name:
                source = f"analysis label '{raw}'"
                break
        if name in raw_labels and source is None:
            source = f"analysis label '{name}'"

        classes.append(
            ClassStats(
                name=name,
                group=group,
                images_with_class=count,
                total_images=total_images,
                image_rate=round(rate, 4),
                train_phase=assign_train_phase(name, rate, count),
                yolo_id=yolo_id,
                analysis_source=source,
            ).__dict__
        )

    train_now = [c["name"] for c in classes if c["train_phase"] == "train_now"]
    train_later = [c["name"] for c in classes if c["train_phase"] == "train_later"]

    return {
        "dataset": {
            "cleaned_images": clean_count,
            "analyzed_images": total_images,
            "analysis_csv": str(ANALYSIS_CSV.relative_to(PROJECT_ROOT)),
            "has_furniture_plans": sum(1 for r in rows if r["has_furniture"] == "True"),
            "line_drawing_plans": sum(1 for r in rows if r["style"] == "line_drawing"),
            "furnished_color_plans": sum(1 for r in rows if r["style"] == "furnished_color"),
        },
        "raw_analysis_labels": dict(raw_labels.most_common()),
        "analysis_aliases": ANALYSIS_ALIASES,
        "train_now_count": len(train_now),
        "train_later_count": len(train_later),
        "train_now": train_now,
        "train_later": train_later,
        "classes": classes,
    }


def main() -> int:
    report = analyze()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["dataset"], indent=2))
    print(f"Train Now ({report['train_now_count']}): {', '.join(report['train_now'])}")
    print(f"Train Later ({report['train_later_count']}): {', '.join(report['train_later'])}")
    print(f"Wrote {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
