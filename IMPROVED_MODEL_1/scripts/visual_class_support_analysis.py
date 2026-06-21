#!/usr/bin/env python3
"""
Read-only visual class-support analysis for dataset_clean/images.

Fuses legacy CSV metadata, style classification, and OpenCV heuristics
to estimate per-class dataset support for the 37-class BIM taxonomy.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = PROJECT_ROOT / "dataset_clean" / "images"
ANALYSIS_CSV = PROJECT_ROOT / "data" / "analysis_all_images.csv"
OUTPUT_JSON = PROJECT_ROOT / "data" / "class_support_analysis.json"

TAXONOMY: list[tuple[int, str, str]] = [
    (0, "wall", "structural"),
    (1, "door", "structural"),
    (2, "window", "structural"),
    (3, "column", "structural"),
    (4, "stair", "structural"),
    (5, "bedroom", "rooms"),
    (6, "dining_room", "rooms"),
    (7, "living_room", "rooms"),
    (8, "study_room", "rooms"),
    (9, "kitchen", "rooms"),
    (10, "bathroom", "rooms"),
    (11, "balcony", "rooms"),
    (12, "utility_room", "rooms"),
    (13, "store_room", "rooms"),
    (14, "corridor", "rooms"),
    (15, "bed", "furniture"),
    (16, "wardrobe", "furniture"),
    (17, "sofa", "furniture"),
    (18, "chair", "furniture"),
    (19, "dining_table", "furniture"),
    (20, "coffee_table", "furniture"),
    (21, "tv_unit", "furniture"),
    (22, "desk", "furniture"),
    (23, "bookshelf", "furniture"),
    (24, "cabinet", "furniture"),
    (25, "dressing_table", "furniture"),
    (26, "side_table", "furniture"),
    (27, "wc", "fixtures"),
    (28, "wash_basin", "fixtures"),
    (29, "shower", "fixtures"),
    (30, "bathtub", "fixtures"),
    (31, "sink", "fixtures"),
    (32, "stove", "appliances"),
    (33, "refrigerator", "appliances"),
    (34, "washing_machine", "appliances"),
    (35, "microwave", "appliances"),
    (36, "chimney", "appliances"),
]

CLASS_NAMES = [name for _, name, _ in TAXONOMY]

CSV_TO_TAXONOMY: dict[str, str] = {
    "wall": "wall",
    "door": "door",
    "window": "window",
    "bedroom": "bedroom",
    "living_room": "living_room",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "bed": "bed",
    "wardrobe": "wardrobe",
    "sofa": "sofa",
    "chair": "chair",
    "table": "dining_table",
    "toilet": "wc",
    "sink": "sink",
    "stove": "stove",
}

ROOM_KEYWORDS: dict[str, list[str]] = {
    "dining_room": ["dining", "dinning", "d/r", "dr "],
    "study_room": ["study", "office", "study room"],
    "balcony": ["balcony", "balc", "terrace", "deck"],
    "utility_room": ["utility", "laundry", "wash area"],
    "store_room": ["store", "storage", "storeroom", "closet room"],
    "corridor": ["corridor", "passage", "hallway", "foyer", "lobby", "entry"],
    "column": ["column", "col."],
    "stair": ["stair", "stairs", "staircase"],
}

FIXTURE_KEYWORDS: dict[str, list[str]] = {
    "wash_basin": ["basin", "wash basin", "vanity"],
    "shower": ["shower"],
    "bathtub": ["bath", "bathtub", "tub"],
    "refrigerator": ["fridge", "refrigerator", "ref"],
    "washing_machine": ["washing", "washer", "w/m"],
    "microwave": ["microwave", "micr"],
    "chimney": ["chimney", "hood"],
}

PRESENCE_THRESHOLD = 0.45


@dataclass
class ImageSignals:
    filename: str
    width: int
    height: int
    style: str
    has_csv: bool
    csv_classes: set[str] = field(default_factory=set)
    has_furniture_csv: bool = False
    edge_density: float = 0.0
    arc_score: float = 0.0
    window_pair_score: float = 0.0
    column_blob_score: float = 0.0
    stair_pattern_score: float = 0.0
    color_blob_score: float = 0.0
    ocr_text: str = ""
    class_probs: dict[str, float] = field(default_factory=dict)


def load_csv_index() -> dict[str, dict[str, str]]:
    if not ANALYSIS_CSV.is_file():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with ANALYSIS_CSV.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[row["filename"]] = row
    return rows


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


def pseudo_ocr_from_filename_and_edges(gray: np.ndarray, filename: str) -> str:
    """Lightweight text proxy: threshold small horizontal text-like components."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = gray.shape
    text_mask = np.zeros_like(binary)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tokens: list[str] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        if ch < 8 or ch > 40 or cw < 8 or area < 40:
            continue
        if cw / max(ch, 1) > 8:
            tokens.append("label_region")
    stem = Path(filename).stem.lower()
    return " ".join(tokens) + " " + stem.replace("-", " ").replace("_", " ")


def keyword_hit(text: str, keywords: list[str]) -> float:
    text_l = text.lower()
    hits = sum(1 for kw in keywords if kw in text_l)
    if hits == 0:
        return 0.0
    return min(1.0, 0.55 + 0.15 * hits)


def analyze_geometry(gray: np.ndarray) -> dict[str, float]:
    h, w = gray.shape
    scale = 1024 / max(h, w)
    if scale < 1.0:
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    edges = cv2.Canny(gray, 60, 180)
    edge_density = float(edges.mean()) / 255.0

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=18,
        param1=80,
        param2=22,
        minRadius=8,
        maxRadius=80,
    )
    arc_score = 0.0
    if circles is not None:
        arc_score = min(1.0, len(circles[0]) / 12.0)

    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, threshold=80, minLineLength=30, maxLineGap=8)
    window_pair_score = 0.0
    if lines is not None and len(lines) > 4:
        horizontals = []
        for line in lines[:200]:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) <= 3 and abs(x2 - x1) > 20:
                horizontals.append((y1, x1, x2))
        horizontals.sort()
        pairs = 0
        for i in range(len(horizontals) - 1):
            y_a, xa1, xa2 = horizontals[i]
            y_b, xb1, xb2 = horizontals[i + 1]
            if 2 <= abs(y_b - y_a) <= 12:
                overlap = max(0, min(xa2, xb2) - max(xa1, xb1))
                if overlap > 15:
                    pairs += 1
        window_pair_score = min(1.0, pairs / 8.0)

    _, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    column_hits = 0
    stair_hits = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 60 or area > 5000:
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = cw / max(ch, 1)
        if 0.75 <= aspect <= 1.35 and 8 <= cw <= 45:
            column_hits += 1
        if 1.8 <= aspect <= 6.0 and ch >= 25:
            stair_hits += 1
    column_blob_score = min(1.0, column_hits / 6.0)
    stair_pattern_score = min(1.0, stair_hits / 4.0)

    return {
        "edge_density": edge_density,
        "arc_score": arc_score,
        "window_pair_score": window_pair_score,
        "column_blob_score": column_blob_score,
        "stair_pattern_score": stair_pattern_score,
    }


def color_furniture_score(bgr: np.ndarray) -> float:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (5, 35, 40), (165, 255, 255))
    ratio = float(mask.mean()) / 255.0
    return min(1.0, ratio * 8.0)


def fuse_class_probs(signals: ImageSignals) -> dict[str, float]:
    probs: dict[str, float] = {name: 0.0 for name in CLASS_NAMES}
    text = signals.ocr_text

    # Structural — near-universal on floor plans
    probs["wall"] = max(probs["wall"], min(0.995, 0.75 + signals.edge_density * 4.0))
    probs["door"] = max(probs["door"], min(0.99, 0.55 + signals.arc_score * 0.4 + signals.edge_density * 2.0))
    probs["window"] = max(
        probs["window"],
        min(0.98, 0.45 + signals.window_pair_score * 0.45 + signals.edge_density * 1.5),
    )
    probs["column"] = max(probs["column"], signals.column_blob_score * 0.65)
    probs["stair"] = max(probs["stair"], signals.stair_pattern_score * 0.70)

    # CSV-backed labels
    for csv_label, tax_name in CSV_TO_TAXONOMY.items():
        if csv_label in signals.csv_classes:
            probs[tax_name] = max(probs[tax_name], 0.92)

    # Room labels from CSV subset
    for room in ("bedroom", "living_room", "kitchen", "bathroom"):
        if room in signals.csv_classes:
            probs[room] = max(probs[room], 0.94)

    # Keyword OCR proxy for rare rooms / elements
    for room, keywords in ROOM_KEYWORDS.items():
        hit = keyword_hit(text, keywords)
        if hit:
            probs[room] = max(probs[room], hit)

    for fixture, keywords in FIXTURE_KEYWORDS.items():
        hit = keyword_hit(text, keywords)
        if hit:
            probs[fixture] = max(probs[fixture], hit)

    # Typical multi-room residential prior for line drawings without explicit labels
    if signals.style == "line_drawing" and signals.edge_density > 0.02:
        for room in ("bedroom", "living_room", "kitchen", "bathroom"):
            if probs[room] < 0.5:
                probs[room] = max(probs[room], 0.72)
        probs["corridor"] = max(probs["corridor"], 0.35)

    # Dining room co-occurrence with kitchen / furnished layouts
    if "kitchen" in signals.csv_classes or probs["kitchen"] > 0.7:
        probs["dining_room"] = max(probs["dining_room"], 0.28)
    if signals.has_furniture_csv or signals.style == "furnished_color":
        probs["dining_room"] = max(probs["dining_room"], 0.42)

    # Furniture — furnished plans only (strong), line drawings weak symbols
    furn_base = 0.0
    if signals.has_furniture_csv:
        furn_base = 0.88
    elif signals.style == "furnished_color":
        furn_base = max(furn_base, 0.55 + signals.color_blob_score * 0.35)
    elif signals.style == "line_drawing":
        furn_base = 0.08

    for furn in (
        "bed",
        "wardrobe",
        "sofa",
        "chair",
        "dining_table",
        "coffee_table",
        "tv_unit",
        "desk",
        "bookshelf",
        "cabinet",
        "dressing_table",
        "side_table",
    ):
        if furn in signals.csv_classes or CSV_TO_TAXONOMY.get(furn) == furn and furn in signals.csv_classes:
            probs[furn] = max(probs[furn], 0.90)
        elif furn in ("bed", "wardrobe", "sofa", "chair", "dining_table") and furn_base > 0.5:
            probs[furn] = max(probs[furn], furn_base * 0.95)
        else:
            probs[furn] = max(probs[furn], furn_base * 0.25)

    # Fixtures — bathroom context
    bath_ctx = probs["bathroom"] > 0.6 or "bathroom" in signals.csv_classes
    if bath_ctx:
        probs["wc"] = max(probs["wc"], 0.55 if signals.style == "line_drawing" else 0.82)
        probs["wash_basin"] = max(probs["wash_basin"], 0.35 if signals.style == "line_drawing" else 0.62)
        probs["shower"] = max(probs["shower"], 0.30 if signals.style == "line_drawing" else 0.55)
        probs["bathtub"] = max(probs["bathtub"], 0.18 if signals.style == "line_drawing" else 0.40)
    if "sink" in signals.csv_classes:
        probs["sink"] = max(probs["sink"], 0.90)
    elif probs["kitchen"] > 0.6:
        probs["sink"] = max(probs["sink"], 0.48)

    # Appliances
    if "stove" in signals.csv_classes:
        probs["stove"] = max(probs["stove"], 0.90)
    elif probs["kitchen"] > 0.6:
        probs["stove"] = max(probs["stove"], 0.35 if signals.style == "line_drawing" else 0.65)
    if signals.style == "furnished_color" and probs["kitchen"] > 0.6:
        probs["refrigerator"] = max(probs["refrigerator"], 0.38)
        probs["microwave"] = max(probs["microwave"], 0.22)
        probs["chimney"] = max(probs["chimney"], 0.25)
    if signals.has_furniture_csv:
        probs["refrigerator"] = max(probs["refrigerator"], 0.45)
        probs["washing_machine"] = max(probs["washing_machine"], 0.32)

    # Balcony / utility / store weak priors
    if signals.style != "line_drawing":
        probs["balcony"] = max(probs["balcony"], 0.22)
    probs["utility_room"] = max(probs["utility_room"], 0.15)
    probs["store_room"] = max(probs["store_room"], 0.12)
    probs["study_room"] = max(probs["study_room"], 0.14)

    return probs


def analyze_image(path: Path, csv_row: dict[str, str] | None) -> ImageSignals:
    data = np.fromfile(path, dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Unreadable image: {path}")

    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    style = csv_row["style"] if csv_row else classify_style(bgr)
    csv_classes: set[str] = set()
    has_furniture_csv = False
    if csv_row:
        csv_classes = set(csv_row["visible_classes"].split(";"))
        has_furniture_csv = csv_row.get("has_furniture") == "True"

    geom = analyze_geometry(gray)
    signals = ImageSignals(
        filename=path.name,
        width=w,
        height=h,
        style=style,
        has_csv=csv_row is not None,
        csv_classes=csv_classes,
        has_furniture_csv=has_furniture_csv,
        edge_density=geom["edge_density"],
        arc_score=geom["arc_score"],
        window_pair_score=geom["window_pair_score"],
        column_blob_score=geom["column_blob_score"],
        stair_pattern_score=geom["stair_pattern_score"],
        color_blob_score=color_furniture_score(bgr),
        ocr_text=pseudo_ocr_from_filename_and_edges(gray, path.name),
    )
    signals.class_probs = fuse_class_probs(signals)
    return signals


def support_level(pct: float) -> str:
    if pct >= 40.0:
        return "High"
    if pct >= 10.0:
        return "Medium"
    return "Low"


def confidence_label(avg_prob: float, csv_backed_rate: float) -> str:
    score = avg_prob * 0.5 + csv_backed_rate * 0.5
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def run_analysis() -> dict:
    csv_index = load_csv_index()
    image_paths = sorted(IMAGE_DIR.glob("*.jpg"))
    total = len(image_paths)
    per_image: list[ImageSignals] = []

    for path in image_paths:
        per_image.append(analyze_image(path, csv_index.get(path.name)))

    class_stats: dict[str, dict] = {}
    for _, name, group in TAXONOMY:
        probs = [img.class_probs[name] for img in per_image]
        present = sum(1 for p in probs if p >= PRESENCE_THRESHOLD)
        csv_backed = sum(
            1
            for img in per_image
            if name in img.csv_classes
            or (name in CSV_TO_TAXONOMY.values() and any(CSV_TO_TAXONOMY.get(k) == name for k in img.csv_classes))
        )
        pct = 100.0 * present / total if total else 0.0
        class_stats[name] = {
            "id": next(i for i, n, _ in TAXONOMY if n == name),
            "group": group,
            "images": present,
            "percent": round(pct, 1),
            "mean_probability": round(float(np.mean(probs)), 3),
            "confidence": confidence_label(float(np.mean(probs)), csv_backed / total if total else 0),
            "support_level": support_level(pct),
            "csv_direct_hits": csv_backed,
        }

    styles = Counter(img.style for img in per_image)
    furnished = sum(1 for img in per_image if img.style == "furnished_color" or img.has_furniture_csv)
    widths = [img.width for img in per_image]
    heights = [img.height for img in per_image]
    megapixels = [img.width * img.height / 1e6 for img in per_image]

    return {
        "total_images": total,
        "images_with_csv_metadata": sum(1 for img in per_image if img.has_csv),
        "images_visual_only": sum(1 for img in per_image if not img.has_csv),
        "style_distribution": dict(styles),
        "furnished_or_furniture_flag": furnished,
        "non_furnished": total - furnished,
        "resolution": {
            "width_min": min(widths),
            "width_max": max(widths),
            "width_median": int(statistics.median(widths)),
            "height_min": min(heights),
            "height_max": max(heights),
            "height_median": int(statistics.median(heights)),
            "megapixels_median": round(statistics.median(megapixels), 2),
        },
        "presence_threshold": PRESENCE_THRESHOLD,
        "classes": class_stats,
        "per_image_sample": [
            {
                "filename": img.filename,
                "style": img.style,
                "top_classes": sorted(img.class_probs.items(), key=lambda x: -x[1])[:8],
            }
            for img in per_image[:5]
        ],
    }


def main() -> int:
    report = run_analysis()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Analyzed {report['total_images']} images -> {OUTPUT_JSON}")
    for name in CLASS_NAMES[:5]:
        s = report["classes"][name]
        print(f"  {name}: {s['images']} ({s['percent']}%) {s['support_level']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
