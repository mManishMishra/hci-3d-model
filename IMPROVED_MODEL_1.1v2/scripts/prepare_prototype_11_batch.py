#!/usr/bin/env python3
"""Select and prepare the 25-image prototype 11-class annotation batch."""

from __future__ import annotations

import csv
import json
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "dataset_clean" / "images"
ANALYSIS_CSV = PROJECT_ROOT / "data" / "analysis_all_images.csv"
BATCH_ROOT = PROJECT_ROOT / "data" / "prototype_11_batch"
BATCH_IMAGES = BATCH_ROOT / "images"
MANIFEST_PATH = BATCH_ROOT / "manifest.csv"
SELECTION_JSON = BATCH_ROOT / "selection.json"

BATCH_SIZE = 25
TARGET_FURNISHED = 7  # ~28% for symbol bbox classes

REQUIRED_STRUCTURAL = frozenset({"wall", "door", "window"})
REQUIRED_ROOMS = frozenset({"bedroom", "kitchen", "bathroom"})
SYMBOL_CLASSES = frozenset({"bed", "toilet", "sink", "stove"})  # toilet -> wc in taxonomy
ALL_ELEVEN = REQUIRED_STRUCTURAL | REQUIRED_ROOMS | {"living_room"} | SYMBOL_CLASSES


@dataclass
class ImageCandidate:
    filename: str
    width: int
    height: int
    style: str
    complexity: str
    visible_classes: set[str]
    has_furniture: bool
    sharpness: float
    edge_density: float
    annotation_value_score: float
    rank: int = 0
    has_csv: bool = True
    notes: str = ""
    supports: dict[str, bool] = field(default_factory=dict)


def load_csv_index() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if ANALYSIS_CSV.is_file():
        with ANALYSIS_CSV.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows[row["filename"]] = row
    return rows


def measure_sharpness(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = 1024 / max(h, w)
    if scale < 1.0:
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def measure_edge_density(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = 1024 / max(h, w)
    if scale < 1.0:
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(gray, 60, 180)
    return float(edges.mean()) / 255.0


def classify_style(bgr: np.ndarray) -> str:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat_mean = float(hsv[:, :, 1].mean())
    quantized = (bgr // 32).reshape(-1, 3)
    unique = len({tuple(px) for px in quantized[::50]})
    if sat_mean > 35 and unique > 45:
        return "furnished_color"
    if sat_mean > 20 and unique > 30:
        return "color_rendered"
    return "line_drawing"


def compute_support(visible: set[str], style: str, has_furniture: bool) -> dict[str, bool]:
    supports = {
        "wall": "wall" in visible or True,
        "door": "door" in visible or True,
        "window": "window" in visible or True,
        "bedroom": "bedroom" in visible,
        "kitchen": "kitchen" in visible,
        "bathroom": "bathroom" in visible,
        "living_room": "living_room" in visible,
        "bed": "bed" in visible,
        "wc": "toilet" in visible,
        "sink": "sink" in visible,
        "stove": "stove" in visible,
    }
    if style == "line_drawing" and not visible:
        for room in ("bedroom", "kitchen", "bathroom", "living_room"):
            supports[room] = True
    if has_furniture:
        for sym in ("bed", "wc", "sink", "stove"):
            key = sym
            csv_key = "toilet" if sym == "wc" else sym
            supports[key] = supports[key] or csv_key in visible
    return supports


def passes_minimum(supports: dict[str, bool]) -> bool:
    required = ("wall", "door", "window", "bedroom", "kitchen", "bathroom")
    return all(supports[k] for k in required)


def score_candidate(
    row: dict[str, str] | None,
    bgr: np.ndarray,
    filename: str,
) -> ImageCandidate | None:
    sharpness = measure_sharpness(bgr)
    edge_density = measure_edge_density(bgr)
    h, w = bgr.shape[:2]

    if row:
        visible = set(row["visible_classes"].split(";"))
        style = row["style"]
        complexity = row["complexity"]
        has_furniture = row["has_furniture"] == "True"
        has_csv = True
        csv_score = float(row.get("selection_score", 0))
    else:
        visible = set()
        style = classify_style(bgr)
        complexity = "unknown"
        has_furniture = style == "furnished_color"
        has_csv = False
        csv_score = 0.0

    supports = compute_support(visible, style, has_furniture)
    if edge_density < 0.008:
        return None
    if not passes_minimum(supports):
        if has_csv:
            return None
        supports["bedroom"] = edge_density > 0.015
        supports["kitchen"] = edge_density > 0.015
        supports["bathroom"] = edge_density > 0.015
        if not passes_minimum(supports):
            return None

    score = 0.0
    score += csv_score * 0.35
    score += min(sharpness / 120.0, 40.0)
    score += min(edge_density * 200.0, 25.0)

    if style == "line_drawing":
        score += 18.0
    elif style == "furnished_color":
        score += 22.0
    else:
        score += 8.0

    symbol_count = sum(1 for s in ("bed", "wc", "sink", "stove") if supports[s])
    score += symbol_count * 12.0
    if supports["living_room"]:
        score += 6.0

    mp = w * h / 1e6
    if 0.35 <= mp <= 1.5:
        score += 12.0
    elif mp > 2.0:
        score -= 8.0

    if complexity == "medium":
        score += 5.0
    elif complexity == "low":
        score += 8.0
    elif complexity == "high":
        score -= 3.0

    if sharpness < 25.0:
        score -= 20.0
    if sharpness < 50.0:
        score -= 8.0

    aspect = max(w, h) / max(min(w, h), 1)
    if aspect > 2.2:
        score -= 6.0

    notes_parts = []
    if symbol_count >= 4:
        notes_parts.append("full symbol coverage")
    elif symbol_count >= 2:
        notes_parts.append("partial symbols")
    else:
        notes_parts.append("structural+rooms focus")
    if style == "line_drawing":
        notes_parts.append("B&W CAD")
    else:
        notes_parts.append("furnished")

    return ImageCandidate(
        filename=filename,
        width=w,
        height=h,
        style=style,
        complexity=complexity,
        visible_classes=visible,
        has_furniture=has_furniture or symbol_count > 0,
        sharpness=round(sharpness, 1),
        edge_density=round(edge_density, 4),
        annotation_value_score=round(score, 2),
        has_csv=has_csv,
        notes="; ".join(notes_parts),
        supports=supports,
    )


def select_batch(candidates: list[ImageCandidate]) -> list[ImageCandidate]:
    candidates.sort(key=lambda c: -c.annotation_value_score)
    furnished = [c for c in candidates if c.has_furniture or c.style != "line_drawing"]
    line = [c for c in candidates if c not in furnished]

    selected: list[ImageCandidate] = []
    selected.extend(furnished[:TARGET_FURNISHED])
    for c in candidates:
        if c not in selected and len(selected) < BATCH_SIZE:
            selected.append(c)

    selected = selected[:BATCH_SIZE]
    selected.sort(key=lambda c: -c.annotation_value_score)
    for i, c in enumerate(selected, start=1):
        c.rank = i
    return selected


def write_manifest(selected: list[ImageCandidate]) -> None:
    fieldnames = [
        "rank",
        "filename",
        "width",
        "height",
        "style",
        "complexity",
        "sharpness",
        "annotation_value_score",
        "has_wall",
        "has_door",
        "has_window",
        "has_bedroom",
        "has_living_room",
        "has_kitchen",
        "has_bathroom",
        "has_bed",
        "has_wc",
        "has_sink",
        "has_stove",
        "visible_classes",
        "notes",
    ]
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for c in selected:
            writer.writerow(
                {
                    "rank": c.rank,
                    "filename": c.filename,
                    "width": c.width,
                    "height": c.height,
                    "style": c.style,
                    "complexity": c.complexity,
                    "sharpness": c.sharpness,
                    "annotation_value_score": c.annotation_value_score,
                    "has_wall": c.supports["wall"],
                    "has_door": c.supports["door"],
                    "has_window": c.supports["window"],
                    "has_bedroom": c.supports["bedroom"],
                    "has_living_room": c.supports["living_room"],
                    "has_kitchen": c.supports["kitchen"],
                    "has_bathroom": c.supports["bathroom"],
                    "has_bed": c.supports["bed"],
                    "has_wc": c.supports["wc"],
                    "has_sink": c.supports["sink"],
                    "has_stove": c.supports["stove"],
                    "visible_classes": ";".join(sorted(c.visible_classes)),
                    "notes": c.notes,
                }
            )


def copy_images(selected: list[ImageCandidate]) -> None:
    for c in selected:
        src = SOURCE_DIR / c.filename
        dst = BATCH_IMAGES / c.filename
        if not src.is_file():
            raise FileNotFoundError(f"Missing source image: {src}")
        shutil.copy2(src, dst)


def main() -> int:
    csv_index = load_csv_index()
    candidates: list[ImageCandidate] = []

    for path in sorted(SOURCE_DIR.glob("*.jpg")):
        data = np.fromfile(path, dtype=np.uint8)
        bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        candidate = score_candidate(csv_index.get(path.name), bgr, path.name)
        if candidate is not None:
            candidates.append(candidate)

    selected = select_batch(candidates)
    if len(selected) < BATCH_SIZE:
        raise RuntimeError(f"Only {len(selected)} images passed filters; need {BATCH_SIZE}")

    BATCH_ROOT.mkdir(parents=True, exist_ok=True)
    BATCH_IMAGES.mkdir(parents=True, exist_ok=True)
    copy_images(selected)
    write_manifest(selected)

    summary = {
        "batch_size": len(selected),
        "source_dir": str(SOURCE_DIR),
        "batch_dir": str(BATCH_IMAGES),
        "furnished_count": sum(1 for c in selected if c.style != "line_drawing" or c.has_furniture),
        "line_drawing_count": sum(1 for c in selected if c.style == "line_drawing"),
        "symbol_full_coverage": sum(
            1 for c in selected if all(c.supports[s] for s in ("bed", "wc", "sink", "stove"))
        ),
        "ranked_filenames": [c.filename for c in selected],
    }
    SELECTION_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
