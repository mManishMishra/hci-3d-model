# logic/yolo_inference.py — shared YOLO inference helpers (Auto Label + Detect)
import glob
import os
from pathlib import Path

import cv2
import numpy as np

from config.classes import CLASS_IDS, ID_TO_CLASS

HCI_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = HCI_DIR.parent

# Same palette as /api/detect in server.py
HCI_COLORS = {
    0: (0, 0, 200),
    1: (255, 0, 255),
    2: (0, 165, 255),
    3: (0, 200, 0),
    4: (100, 100, 100),
    5: (80, 80, 80),
    6: (255, 165, 0),
    7: (139, 69, 19),
    8: (100, 100, 255),
    9: (180, 180, 180),
    10: (200, 150, 150),
    11: (200, 200, 0),
    12: (210, 180, 140),
    13: (255, 255, 165),
    14: (165, 165, 255),
    15: (165, 255, 165),
    16: (255, 200, 100),
}

PRIORITY_HCI_CLASSES = frozenset({"Wall", "Door", "Window"})

_NAME_ALIASES = {
    "wall": "Wall",
    "walls": "Wall",
    "door": "Door",
    "doors": "Door",
    "window": "Window",
    "windows": "Window",
    "section door": "Door",
}

_model_cache = {"path": None, "model": None}


def contour_to_yolo_seg(cnt, img_w, img_h, cid):
    if cnt is None or len(cnt) < 3:
        return ""
    flat = cnt.flatten()
    coords = []
    for i in range(0, len(flat), 2):
        coords.append(f"{flat[i] / img_w:.6f} {flat[i + 1] / img_h:.6f}")
    return f"{cid} " + " ".join(coords)


class ModelNotFoundError(FileNotFoundError):
    """Raised when no YOLO weights are available for inference."""


def find_model_path() -> str:
    """Resolve active model — mirrors server._find_best_model()."""
    active = PROJECT_ROOT / "best_gdrive.pt"
    if active.exists():
        return str(active)

    known = PROJECT_ROOT / "IMPROVED_MODEL_1.1" / "runs" / "pilot_wall_door_v0_1" / "weights" / "best.pt"
    if known.exists():
        return str(known)

    search_roots = [
        PROJECT_ROOT / "gdrive_dataset" / "runs",
        PROJECT_ROOT / "runs",
        PROJECT_ROOT / "iterations",
        PROJECT_ROOT / "IMPROVED_MODEL_1.1" / "runs",
        HCI_DIR / "gdrive_dataset" / "runs",
        HCI_DIR / "IMPROVED_MODEL_1.1" / "runs",
    ]
    candidates: list[str] = []
    best_path, best_map = "", 0.0
    for root in search_roots:
        if not root.is_dir():
            continue
        for pt in sorted(glob.glob(str(root / "**" / "best.pt"), recursive=True)):
            if pt not in candidates:
                candidates.append(pt)
            try:
                from ultralytics import YOLO as _YOLO

                m = _YOLO(pt)
                tr = (m.ckpt or {}).get("train_results", {})
                map50_list = tr.get("metrics/mAP50(B)", [0])
                map50 = max(map50_list) if map50_list else 0.0
                if map50 > best_map:
                    best_map = map50
                    best_path = pt
            except Exception:
                pass
    if best_path:
        return best_path
    if candidates:
        return candidates[0]
    return ""


def map_model_class_to_hci(model_cls_id: int, model_names: dict) -> str | None:
    """Map a YOLO model class id to an HCI class name (Wall/Door/Window only)."""
    raw = model_names.get(int(model_cls_id), str(model_cls_id))
    if isinstance(raw, (list, tuple)):
        raw = raw[0]
    raw_str = str(raw).strip()
    if raw_str in CLASS_IDS and raw_str in PRIORITY_HCI_CLASSES:
        return raw_str
    key = raw_str.lower().replace("_", " ")
    hci = _NAME_ALIASES.get(key)
    if hci and hci in PRIORITY_HCI_CLASSES:
        return hci
    for name in PRIORITY_HCI_CLASSES:
        if raw_str.lower() == name.lower():
            return name
    return None


def _get_model(model_path: str | None = None):
    path = model_path or find_model_path()
    if not path or not os.path.exists(path):
        raise ModelNotFoundError(
            f"No YOLO model found. Place weights at {PROJECT_ROOT / 'best_gdrive.pt'} "
            f"or train via the UI first."
        )
    if _model_cache["path"] == path and _model_cache["model"] is not None:
        return _model_cache["model"], path
    from ultralytics import YOLO

    model = YOLO(path)
    _model_cache["path"] = path
    _model_cache["model"] = model
    return model, path


def _filter_contour(cnt: np.ndarray, img_h: int, img_w: int) -> np.ndarray | None:
    if cnt is None or len(cnt) < 3:
        return None
    area = cv2.contourArea(cnt)
    min_area = max(16.0, 0.00005 * img_h * img_w)
    if area < min_area:
        return None
    peri = cv2.arcLength(cnt, True)
    eps = max(1.0, 0.002 * peri)
    approx = cv2.approxPolyDP(cnt, eps, True)
    if approx is None or len(approx) < 3:
        return None
    return approx


def _bbox_to_contour(x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
    pts = np.array(
        [[int(x1), int(y1)], [int(x2), int(y1)], [int(x2), int(y2)], [int(x1), int(y2)]],
        dtype=np.int32,
    ).reshape(-1, 1, 2)
    return pts


def run_yolo_inference(
    img: np.ndarray,
    model_path: str | None = None,
    conf: float = 0.05,
    imgsz: int = 640,
    retry_conf: float = 0.001,
) -> tuple[dict, list[str], str]:
    """
    Run YOLO on img; return (labelled_dict, yolo_label_lines, model_path_used).
    labelled_dict keys use HCI PascalCase: Wall, Door, Window.
    """
    if img is None:
        raise ValueError("image unreadable")

    img_h, img_w = img.shape[:2]
    model, used_path = _get_model(model_path)
    labelled: dict = {}
    label_lines: list[str] = []
    confs = [conf, retry_conf]

    for attempt_conf in confs:
        labelled.clear()
        label_lines.clear()
        results = model.predict(img, imgsz=imgsz, conf=attempt_conf, verbose=False)
        result = results[0]
        boxes = result.boxes
        masks = result.masks

        if masks is not None and boxes is not None and len(boxes) > 0:
            mask_data = masks.data.cpu().numpy()
            box_data = boxes.data.cpu().numpy()
            for i, box in enumerate(box_data):
                cls_id = int(box[5])
                hci_name = map_model_class_to_hci(cls_id, model.names)
                if hci_name is None:
                    continue
                hci_cid = CLASS_IDS[hci_name]
                mask = mask_data[i]
                if mask.shape != (img_h, img_w):
                    mask = cv2.resize(mask, (img_w, img_h))
                mask_bin = (mask > 0.5).astype(np.uint8)
                cnts, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in cnts:
                    clean = _filter_contour(cnt, img_h, img_w)
                    if clean is None:
                        continue
                    labelled.setdefault(hci_name, []).append(clean)
                    line = contour_to_yolo_seg(clean, img_w, img_h, hci_cid)
                    if line:
                        label_lines.append(line)

        elif boxes is not None and len(boxes) > 0:
            box_data = boxes.data.cpu().numpy()
            for box in box_data:
                cls_id = int(box[5])
                hci_name = map_model_class_to_hci(cls_id, model.names)
                if hci_name is None:
                    continue
                hci_cid = CLASS_IDS[hci_name]
                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                cnt = _bbox_to_contour(x1, y1, x2, y2)
                clean = _filter_contour(cnt, img_h, img_w)
                if clean is None:
                    continue
                labelled.setdefault(hci_name, []).append(clean)
                line = contour_to_yolo_seg(clean, img_w, img_h, hci_cid)
                if line:
                    label_lines.append(line)

        if label_lines:
            break

    return labelled, label_lines, used_path


def draw_detection_overlay(img: np.ndarray, labelled: dict) -> np.ndarray:
    """Draw colored filled polygons + class labels (same style as /api/detect)."""
    vis = img.copy()
    img_h, img_w = img.shape[:2]
    max_dim = max(img_h, img_w)
    font_scale = max(0.4, max_dim / 2500.0)
    thick = max(1, int(max_dim * 0.002))

    for cls_name, contours in labelled.items():
        if cls_name.startswith("_") or not isinstance(contours, list):
            continue
        hci_id = CLASS_IDS.get(cls_name, 3)
        color = HCI_COLORS.get(hci_id, (128, 128, 128))
        for cnt in contours:
            if cnt is None or len(cnt) < 3:
                continue
            mask = np.zeros((img_h, img_w), dtype=np.uint8)
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            overlay = vis.copy()
            overlay[mask > 0] = color
            vis = cv2.addWeighted(overlay, 0.3, vis, 0.7, 0)
            cv2.drawContours(vis, [cnt], -1, color, thick)
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(
                    vis,
                    cls_name,
                    (cx, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    color,
                    thick,
                    cv2.LINE_AA,
                )
    return vis
