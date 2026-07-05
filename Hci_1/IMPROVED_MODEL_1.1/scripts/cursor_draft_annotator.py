#!/usr/bin/env python3
"""
Draft floor-plan annotator for AI-assisted annotation evaluation.

Produces overlay PNGs, JSON annotations, and quality reports under
D:/HCI_interor/cursor_annotation_output/

Rules source: IMPROVED_MODEL_1/docs/PROTOTYPE_ANNOTATION_GUIDE.md
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "data" / "prototype_11_batch" / "images"
MANIFEST = PROJECT_ROOT / "data" / "prototype_11_batch" / "manifest.csv"
OUTPUT_ROOT = Path(r"D:\HCI_interor\cursor_annotation_output")

WALL_COLOR = (0, 0, 255)      # BGR red
DOOR_COLOR = (0, 204, 0)        # BGR green
WINDOW_COLOR = (255, 102, 0)    # BGR blue-ish

REPRESENTATIVE_FIVE = [
    "2a0e67cffb7acbf83547afdac272caa5.jpg",  # line_drawing, medium B&W
    "8c6c7571c8fa3d65b33b60611626d13a.jpg",  # line_drawing
    "ccc951d1-7ce8-4546-ba57-99423b65202b.jpg",  # line_drawing B&W CAD
    "b92184c9a460e92fd303799fa50f750b.jpg",  # furnished, compact
    "69a35f1cab485159de27a6085a5a9813.jpg",  # furnished
]


@dataclass
class PolygonAnn:
    polygon: list[list[int]]
    confidence: float = 0.5
    source: str = "heuristic"


@dataclass
class ImageAnnotations:
    image: str
    width: int
    height: int
    style: str
    walls: list[PolygonAnn] = field(default_factory=list)
    doors: list[PolygonAnn] = field(default_factory=list)
    windows: list[PolygonAnn] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("cursor_draft_annotator")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(log_dir / "annotation_run.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def load_manifest() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if MANIFEST.is_file():
        with MANIFEST.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows[row["filename"]] = row
    return rows


def polygon_area(poly: list[list[int]]) -> float:
    if len(poly) < 3:
        return 0.0
    arr = np.array(poly, dtype=np.float64)
    x = arr[:, 0]
    y = arr[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def polygon_bbox(poly: list[list[int]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def rect_polygon(x1: int, y1: int, x2: int, y2: int) -> list[list[int]]:
    return [
        [int(x1), int(y1)],
        [int(x2), int(y1)],
        [int(x2), int(y2)],
        [int(x1), int(y2)],
    ]


def native_polygon(poly: list[list[int]]) -> list[list[int]]:
    return [[int(p[0]), int(p[1])] for p in poly]


def clip_polygon(poly: list[list[int]], w: int, h: int) -> list[list[int]]:
    clipped = []
    for x, y in poly:
        clipped.append([int(max(0, min(w - 1, x))), int(max(0, min(h - 1, y)))])
    return clipped


def iou_poly(a: list[list[int]], b: list[list[int]]) -> float:
    ax1, ay1, ax2, ay2 = polygon_bbox(a)
    bx1, by1, bx2, by2 = polygon_bbox(b)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / (area_a + area_b - inter)


def merge_intervals(intervals: list[tuple[int, int]], gap: int = 6) -> list[tuple[int, int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        prev_s, prev_e = merged[-1]
        if start <= prev_e + gap:
            merged[-1] = (prev_s, max(prev_e, end))
        else:
            merged.append((start, end))
    return merged


def subtract_intervals(span: tuple[int, int], holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    segments = [span]
    for hs, he in sorted(holes):
        new_segments: list[tuple[int, int]] = []
        for s, e in segments:
            if he <= s or hs >= e:
                new_segments.append((s, e))
                continue
            if s < hs:
                new_segments.append((s, hs))
            if he < e:
                new_segments.append((he, e))
        segments = new_segments
    return [(s, e) for s, e in segments if e - s >= 8]


def preprocess_binary(bgr: np.ndarray, style: str) -> tuple[np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    margin = int(min(h, w) * 0.02)
    gray_crop = gray[margin : h - margin, margin : w - margin]

    if style == "line_drawing":
        blur = cv2.GaussianBlur(gray_crop, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    else:
        blur = cv2.bilateralFilter(gray_crop, 7, 50, 50)
        dark = cv2.inRange(blur, 0, 85)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        binary = cv2.bitwise_or(dark, otsu)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    full = np.zeros_like(gray)
    full[margin : h - margin, margin : w - margin] = binary
    edges = cv2.Canny(full, 50, 150, apertureSize=3)
    return full, edges


def estimate_wall_thickness(binary: np.ndarray) -> int:
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    vals = dist[dist > 1.0]
    if vals.size == 0:
        return 10
    peak = float(np.percentile(vals, 85))
    thickness = int(max(6, min(24, round(peak * 2))))
    return thickness


def detect_hv_lines(edges: np.ndarray, min_len: int = 25) -> tuple[list[tuple], list[tuple]]:
    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180, threshold=45, minLineLength=min_len, maxLineGap=6
    )
    horiz: list[tuple] = []
    vert: list[tuple] = []
    if lines is None:
        return horiz, vert
    for x1, y1, x2, y2 in lines[:, 0]:
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < min_len:
            continue
        angle = abs(math.degrees(math.atan2(dy, dx)))
        if angle <= 12 or angle >= 168:
            horiz.append((min(x1, x2), max(x1, x2), int(round((y1 + y2) / 2))))
        elif 78 <= angle <= 102:
            vert.append((int(round((x1 + x2) / 2)), min(y1, y2), max(y1, y2)))
    return horiz, vert


def cluster_lines(
    horiz: list[tuple], vert: list[tuple], tol: int
) -> tuple[list[list[tuple]], list[list[tuple]]]:
    def cluster(items: list[tuple], key_idx: int) -> list[list[tuple]]:
        if not items:
            return []
        items = sorted(items, key=lambda t: t[key_idx])
        clusters: list[list[tuple]] = [[items[0]]]
        for item in items[1:]:
            if abs(item[key_idx] - clusters[-1][-1][key_idx]) <= tol:
                clusters[-1].append(item)
            else:
                clusters.append([item])
        return clusters

    return cluster(horiz, 2), cluster(vert, 0)


def wall_rects_from_clusters(
    clusters: list[list[tuple]],
    orientation: str,
    thickness: int,
    openings: list[tuple[int, int, int, int]],
    w: int,
    h: int,
) -> list[PolygonAnn]:
    rects: list[PolygonAnn] = []
    half = max(3, thickness // 2)
    pair_tol = max(4, int(thickness * 0.75))

    for cluster in clusters:
        if len(cluster) < 2:
            continue
        coords = sorted({c[2 if orientation == "h" else 0] for c in cluster})
        for i in range(len(coords) - 1):
            c1, c2 = coords[i], coords[i + 1]
            if not (thickness - 4 <= c2 - c1 <= thickness + 10):
                continue
            y_center = (c1 + c2) // 2 if orientation == "h" else None
            x_center = (c1 + c2) // 2 if orientation == "v" else None
            spans: list[tuple[int, int]] = []
            for seg in cluster:
                if orientation == "h":
                    if abs(seg[2] - y_center) > pair_tol:
                        continue
                    spans.append((seg[0], seg[1]))
                else:
                    if abs(seg[0] - x_center) > pair_tol:
                        continue
                    spans.append((seg[1], seg[2]))
            for start, end in merge_intervals(spans):
                hole_intervals = []
                for ox1, oy1, ox2, oy2 in openings:
                    if orientation == "h":
                        if oy1 <= y_center <= oy2 or abs(((oy1 + oy2) // 2) - y_center) <= half + 4:
                            hole_intervals.append((ox1, ox2))
                    else:
                        if ox1 <= x_center <= ox2 or abs(((ox1 + ox2) // 2) - x_center) <= half + 4:
                            hole_intervals.append((oy1, oy2))
                for seg_start, seg_end in subtract_intervals((start, end), hole_intervals):
                    if orientation == "h":
                        poly = rect_polygon(
                            seg_start, y_center - half, seg_end, y_center + half
                        )
                    else:
                        poly = rect_polygon(
                            x_center - half, seg_start, x_center + half, seg_end
                        )
                    if polygon_area(poly) >= 80:
                        rects.append(PolygonAnn(poly, confidence=0.55, source="hough_pair"))
    return rects


def detect_openings(binary: np.ndarray, thickness: int) -> list[tuple[int, int, int, int]]:
    """Return bounding boxes of likely door/window gaps in wall mask."""
    inv = cv2.bitwise_not(binary)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    inv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    openings: list[tuple[int, int, int, int]] = []
    min_gap = max(10, thickness)
    max_gap = max(80, thickness * 6)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < min_gap * min_gap or area > max_gap * max_gap * 3:
            continue
        aspect = max(w, h) / max(1, min(w, h))
        if 1.2 <= aspect <= 8.0:
            openings.append((x, y, x + w, y + h))
    return openings


def detect_door_arcs(edges: np.ndarray, h: int, w: int) -> list[PolygonAnn]:
    doors: list[PolygonAnn] = []
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    for cnt in contours:
        if len(cnt) < 12:
            continue
        peri = cv2.arcLength(cnt, True)
        area = cv2.contourArea(cnt)
        if area < 80 or area > 8000:
            continue
        circularity = 4 * math.pi * area / max(1.0, peri * peri)
        if 0.15 <= circularity <= 0.85:
            x, y, bw, bh = cv2.boundingRect(cnt)
            if 10 <= bw <= 90 and 10 <= bh <= 90:
                pad = 3
                poly = clip_polygon(
                    rect_polygon(x - pad, y - pad, x + bw + pad, y + bh + pad), w, h
                )
                doors.append(PolygonAnn(poly, confidence=0.35, source="arc_contour"))
    return doors


def detect_window_symbols(binary: np.ndarray, thickness: int, w: int, h: int) -> list[PolygonAnn]:
    windows: list[PolygonAnn] = []
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (max(8, thickness * 2), 3))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, max(8, thickness * 2)))
    hits = cv2.add(
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_h),
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v),
    )
    contours, _ = cv2.findContours(hits, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        area = bw * bh
        if area < 60 or area > 4000:
            continue
        aspect = max(bw, bh) / max(1, min(bw, bh))
        if 1.5 <= aspect <= 12:
            pad = 2
            poly = clip_polygon(
                rect_polygon(x - pad, y - pad, x + bw + pad, y + bh + pad), w, h
            )
            windows.append(PolygonAnn(poly, confidence=0.3, source="window_morph"))
    return windows


def dedupe_polygons(items: list[PolygonAnn], iou_thresh: float = 0.55) -> list[PolygonAnn]:
    kept: list[PolygonAnn] = []
    for item in sorted(items, key=lambda a: a.confidence, reverse=True):
        if any(iou_poly(item.polygon, k.polygon) > iou_thresh for k in kept):
            continue
        kept.append(item)
    return kept


def wall_mask_segments(binary: np.ndarray, thickness: int, w: int, h: int) -> list[PolygonAnn]:
    """Fallback: connected-component wall blobs split into oriented rectangles."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, thickness // 2), max(3, thickness // 2)))
    merged = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects: list[PolygonAnn] = []
    img_area = w * h
    min_area = max(100, thickness * thickness * 2)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > img_area * 0.12:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if max(bw, bh) < thickness:
            continue
        if min(bw, bh) > max(bw, bh) * 0.45 and area > img_area * 0.01:
            continue  # likely room blob, not wall strip
        rect = cv2.minAreaRect(cnt)
        (_, _), (rw, rh), _ = rect
        if min(rw, rh) < max(4, thickness * 0.35):
            continue
        if max(rw, rh) / max(1.0, min(rw, rh)) > 35:
            continue
        box = cv2.boxPoints(rect)
        poly = clip_polygon([[int(p[0]), int(p[1])] for p in box], w, h)
        if polygon_area(poly) >= min_area:
            rects.append(PolygonAnn(poly, confidence=0.4, source="component_rect"))
    return rects


def annotate_image(path: Path, style: str) -> ImageAnnotations:
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(path)
    h, w = bgr.shape[:2]
    result = ImageAnnotations(image=path.name, width=w, height=h, style=style)

    binary, edges = preprocess_binary(bgr, style)
    thickness = estimate_wall_thickness(binary)
    openings = detect_openings(binary, thickness)

    horiz, vert = detect_hv_lines(edges, min_len=max(20, thickness * 2))
    h_clusters, v_clusters = cluster_lines(horiz, vert, tol=max(4, thickness // 2))

    walls_h = wall_rects_from_clusters(h_clusters, "h", thickness, openings, w, h)
    walls_v = wall_rects_from_clusters(v_clusters, "v", thickness, openings, w, h)
    walls = dedupe_polygons(walls_h + walls_v)

    if len(walls) < 8:
        result.warnings.append("low wall count from line-pair method; using component fallback")
        component_walls = wall_mask_segments(binary, thickness, w, h)
        walls = dedupe_polygons(walls + component_walls)

    if len(walls) < 5 and style != "line_drawing":
        result.warnings.append("using dark-region wall fallback for furnished plan")
        walls = dedupe_polygons(walls + wall_mask_segments(binary, thickness, w, h))

    doors = dedupe_polygons(detect_door_arcs(edges, h, w), iou_thresh=0.4)
    windows = dedupe_polygons(
        detect_window_symbols(binary, thickness, w, h), iou_thresh=0.45
    )

    # Remove wall polygons overlapping door/window bboxes
    openings_all = doors + windows
    filtered_walls: list[PolygonAnn] = []
    for wall in walls:
        wx1, wy1, wx2, wy2 = polygon_bbox(wall.polygon)
        w_area = max(1, (wx2 - wx1) * (wy2 - wy1))
        overlap = False
        for op in openings_all:
            ox1, oy1, ox2, oy2 = polygon_bbox(op.polygon)
            ix1, iy1 = max(wx1, ox1), max(wy1, oy1)
            ix2, iy2 = min(wx2, ox2), min(wy2, oy2)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                if inter / w_area > 0.35:
                    overlap = True
                    break
        if not overlap:
            filtered_walls.append(wall)
    walls = filtered_walls

    result.walls = [PolygonAnn(native_polygon(w.polygon), w.confidence, w.source) for w in walls]
    result.doors = [PolygonAnn(native_polygon(d.polygon), d.confidence, d.source) for d in doors]
    result.windows = [PolygonAnn(native_polygon(w.polygon), w.confidence, w.source) for w in windows]

    post_filter_annotations(result)

    # Quality warnings
    img_area = w * h
    walls = result.walls
    doors = result.doors
    windows = result.windows

    if len(walls) < 10:
        result.warnings.append(f"low wall count ({len(walls)}); expect 15-40 for typical plans")
    if len(walls) > 80:
        result.warnings.append(f"high wall count ({len(walls)}); possible over-segmentation")
    if style != "line_drawing":
        result.warnings.append("furnished/color plan — lower confidence; manual review required")

    large_walls = [
        wall for wall in walls if polygon_area(wall.polygon) > img_area * 0.02
    ]
    if large_walls:
        result.warnings.append(
            f"possible merged walls ({len(large_walls)} polygons >2% image area)"
        )

    thin_walls = []
    for wall in walls:
        x1, y1, x2, y2 = polygon_bbox(wall.polygon)
        if min(x2 - x1, y2 - y1) < max(4, thickness // 2):
            thin_walls.append(wall)
    if thin_walls and len(thin_walls) > len(walls) * 0.3:
        result.warnings.append(
            f"possible centerline walls ({len(thin_walls)} thin polygons)"
        )

    if len(doors) == 0:
        result.warnings.append("no doors detected — uncertain door locations")
    if len(windows) == 0:
        result.warnings.append("no windows detected — ambiguous or missing window symbols")

    return result


def filter_by_confidence(items: list[PolygonAnn], max_count: int, min_conf: float) -> list[PolygonAnn]:
    kept = [i for i in items if i.confidence >= min_conf]
    kept = sorted(kept, key=lambda a: a.confidence, reverse=True)[:max_count]
    return kept


def post_filter_annotations(ann: ImageAnnotations) -> None:
    """Reduce false positives — precision over recall for draft review."""
    if ann.style == "line_drawing":
        ann.doors = filter_by_confidence(ann.doors, max_count=18, min_conf=0.32)
        ann.windows = filter_by_confidence(ann.windows, max_count=22, min_conf=0.28)
        if len(ann.walls) > 90:
            ann.walls = filter_by_confidence(ann.walls, max_count=90, min_conf=0.42)
            ann.warnings.append(
                f"wall count capped to {len(ann.walls)} (heuristic over-segmentation trimmed)"
            )
    else:
        ann.doors = filter_by_confidence(ann.doors, max_count=15, min_conf=0.34)
        ann.windows = filter_by_confidence(ann.windows, max_count=18, min_conf=0.30)
        ann.walls = filter_by_confidence(ann.walls, max_count=45, min_conf=0.38)

    if len(ann.doors) >= 15:
        ann.warnings.append("many door candidates retained — verify each manually")
    if len(ann.windows) >= 15:
        ann.warnings.append("many window candidates retained — verify each manually")


def draw_overlay(bgr: np.ndarray, ann: ImageAnnotations) -> np.ndarray:
    overlay = bgr.copy()
    for wall in ann.walls:
        pts = np.array(wall.polygon, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], WALL_COLOR)
        cv2.polylines(overlay, [pts], True, (0, 0, 180), 1)
    for door in ann.doors:
        pts = np.array(door.polygon, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], DOOR_COLOR)
        cv2.polylines(overlay, [pts], True, (0, 120, 0), 1)
    for window in ann.windows:
        pts = np.array(window.polygon, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], WINDOW_COLOR)
        cv2.polylines(overlay, [pts], True, (180, 60, 0), 1)
    return cv2.addWeighted(bgr, 0.55, overlay, 0.45, 0)


def save_outputs(ann: ImageAnnotations, bgr: np.ndarray, out_root: Path) -> None:
    stem = Path(ann.image).stem
    overlay_dir = out_root / "overlays"
    json_dir = out_root / "json"
    report_dir = out_root / "reports"
    for d in (overlay_dir, json_dir, report_dir):
        d.mkdir(parents=True, exist_ok=True)

    overlay = draw_overlay(bgr, ann)
    cv2.imwrite(str(overlay_dir / f"{stem}.png"), overlay)

    payload = {
        "image": ann.image,
        "width": ann.width,
        "height": ann.height,
        "style": ann.style,
        "annotations": {
            "wall": [{"polygon": w.polygon} for w in ann.walls],
            "door": [{"polygon": d.polygon} for d in ann.doors],
            "window": [{"polygon": w.polygon} for w in ann.windows],
        },
        "draft": True,
        "note": "NOT ground truth — for manual review only",
    }
    with (json_dir / f"{stem}.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    report = {
        "image": ann.image,
        "style": ann.style,
        "wall_count": len(ann.walls),
        "door_count": len(ann.doors),
        "window_count": len(ann.windows),
        "warnings": ann.warnings,
        "avg_wall_confidence": round(
            float(np.mean([w.confidence for w in ann.walls])) if ann.walls else 0.0, 3
        ),
    }
    with (report_dir / f"{stem}.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


def process_images(image_paths: list[Path], manifest: dict[str, dict[str, str]], logger: logging.Logger, out_root: Path) -> list[ImageAnnotations]:
    results: list[ImageAnnotations] = []
    for path in image_paths:
        style = manifest.get(path.name, {}).get("style", "furnished_color")
        logger.info("Processing %s (style=%s)", path.name, style)
        try:
            bgr = cv2.imread(str(path))
            ann = annotate_image(path, style)
            save_outputs(ann, bgr, out_root)
            logger.info(
                "  walls=%d doors=%d windows=%d warnings=%d",
                len(ann.walls),
                len(ann.doors),
                len(ann.windows),
                len(ann.warnings),
            )
            results.append(ann)
        except Exception as exc:
            logger.exception("Failed on %s: %s", path.name, exc)
    return results


def write_summary(results: list[ImageAnnotations], out_root: Path, batch_label: str) -> None:
    total_walls = sum(len(r.walls) for r in results)
    total_doors = sum(len(r.doors) for r in results)
    total_windows = sum(len(r.windows) for r in results)

    warning_counts: dict[str, int] = {}
    for r in results:
        for w in r.warnings:
            key = w.split("(")[0].strip()
            warning_counts[key] = warning_counts.get(key, 0) + 1

    line_styles = [r for r in results if r.style == "line_drawing"]
    furnished = [r for r in results if r.style != "line_drawing"]

    lines = [
        "# Cursor Draft Annotation Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Batch: **{batch_label}**",
        f"Guide: `IMPROVED_MODEL_1/docs/PROTOTYPE_ANNOTATION_GUIDE.md`",
        "",
        "## Totals",
        "",
        f"- Images processed: **{len(results)}**",
        f"- Wall annotations: **{total_walls}** (avg {total_walls / max(1, len(results)):.1f}/image)",
        f"- Door annotations: **{total_doors}** (avg {total_doors / max(1, len(results)):.1f}/image)",
        f"- Window annotations: **{total_windows}** (avg {total_windows / max(1, len(results)):.1f}/image)",
        "",
        "## By image style",
        "",
        f"- Line drawings: {len(line_styles)} images",
        f"- Furnished/color: {len(furnished)} images",
        "",
        "## Common warnings",
        "",
    ]
    for msg, count in sorted(warning_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {msg}: {count} images")

    lines.extend(
        [
            "",
            "## Known limitations (draft quality)",
            "",
            "- Heuristic CV only — no trained floor-plan model",
            "- Furnished/color plans: walls often merged with furniture edges",
            "- Door arcs and window symbols produce false positives",
            "- Curved walls are approximated poorly",
            "- T-junction splitting is incomplete on complex plans",
            "",
            "## Estimated manual correction effort",
            "",
            "| Style | Est. correction time/image | Notes |",
            "|-------|---------------------------|-------|",
            "| line_drawing | 25–45 min | Delete false walls, fix junction splits, add missed openings |",
            "| furnished_color | 45–75 min | Heavy cleanup; many false positives |",
            "",
            f"**Pilot (5 images):** ~3–5 hours manual correction",
            f"**Full batch ({len(results)} images):** ~{len(results) * 0.75:.0f}–{len(results) * 1.1:.0f} hours",
            "",
            "## Output locations",
            "",
            "- Overlays: `cursor_annotation_output/overlays/`",
            "- JSON: `cursor_annotation_output/json/`",
            "- Reports: `cursor_annotation_output/reports/`",
            "- Logs: `cursor_annotation_output/logs/`",
            "",
            "## Per-image counts",
            "",
            "| Image | Style | Walls | Doors | Windows | Warnings |",
            "|-------|-------|------:|------:|--------:|---------:|",
        ]
    )
    for r in sorted(results, key=lambda x: x.image):
        lines.append(
            f"| {r.image} | {r.style} | {len(r.walls)} | {len(r.doors)} | {len(r.windows)} | {len(r.warnings)} |"
        )

    summary_path = out_root / "summary.md"
    if batch_label == "representative_5" and (out_root / "summary.md").exists():
        summary_path = out_root / "summary_pilot5.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft floor-plan annotator")
    parser.add_argument("--pilot", action="store_true", help="Process 5 representative images only")
    parser.add_argument("--all", action="store_true", help="Process all images in input folder")
    args = parser.parse_args()

    out_root = OUTPUT_ROOT
    logger = setup_logging(out_root / "logs")
    manifest = load_manifest()

    if args.all:
        image_paths = sorted(INPUT_DIR.glob("*.jpg"))
        batch_label = "full_batch"
    else:
        image_paths = [INPUT_DIR / name for name in REPRESENTATIVE_FIVE]
        batch_label = "representative_5"

    missing = [p for p in image_paths if not p.is_file()]
    if missing:
        logger.error("Missing images: %s", ", ".join(p.name for p in missing))
        return 1

    logger.info("Starting batch=%s count=%d", batch_label, len(image_paths))
    results = process_images(image_paths, manifest, logger, out_root)
    write_summary(results, out_root, batch_label)
    logger.info("Done. Summary written to %s", out_root / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
