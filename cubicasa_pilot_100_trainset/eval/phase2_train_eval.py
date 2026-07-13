#!/usr/bin/env python3
"""Day-2 Phase 2: offline train + val preds + compare. Isolated trainset only."""
from __future__ import annotations

import csv
import json
import traceback
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(r"D:\HCI_interor\cubicasa_pilot_100_trainset")
YAML = ROOT / "dataset.yaml"
BASE = Path(r"D:\HCI_interor\yolov8n-seg.pt")
BEST_GDRIVE = Path(r"D:\HCI_interor\best_gdrive.pt")
GDRIVE_DS = Path(r"D:\HCI_interor\gdrive_dataset")
PROJECT = ROOT / "runs"
NAME = "pilot100_offline"
PRED_VAL = ROOT / "eval" / "preds_val"
PRED_BG = ROOT / "eval" / "preds_best_gdrive"
SUMMARY = ROOT / "eval" / "comparison_summary.txt"

CLASS_NAMES = {0: "Room", 1: "Window", 2: "Door", 3: "Wall"}
COLORS = {
    0: (255, 0, 0),
    1: (255, 0, 255),
    2: (0, 165, 255),
    3: (0, 200, 0),
}


def snapshot(path: Path) -> tuple[float | None, int | None]:
    if not path.exists():
        return None, None
    st = path.stat()
    return st.st_mtime, st.st_size


def draw_preds(img: np.ndarray, result) -> np.ndarray:
    vis = img.copy()
    if result.masks is None or result.boxes is None:
        return vis
    masks = result.masks.data.cpu().numpy()
    cls_ids = result.boxes.cls.cpu().numpy().astype(int)
    h, w = vis.shape[:2]
    for mask, cid in zip(masks, cls_ids):
        color = COLORS.get(int(cid), (128, 128, 128))
        m = cv2.resize(mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        bin_m = m > 0.5
        if not bin_m.any():
            continue
        overlay = vis.copy()
        overlay[bin_m] = color
        vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
        cnts, _ = cv2.findContours(bin_m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, color, 2)
    return vis


def save_split_preds(model: YOLO, img_dir: Path, out_dir: Path, conf: float = 0.25) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for img_path in sorted(img_dir.glob("*.png")):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        results = model.predict(source=str(img_path), imgsz=640, conf=conf, verbose=False)
        vis = draw_preds(img, results[0])
        cv2.imwrite(str(out_dir / f"{img_path.stem}_pred.jpg"), vis)
        n += 1
    return n


def parse_results_csv(csv_path: Path) -> dict:
    out = {}
    if not csv_path.exists():
        return out
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return out
    last = rows[-1]
    # Ultralytics column names vary slightly by version
    def pick(row, keys):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                try:
                    return float(row[k])
                except ValueError:
                    pass
        return None

    out["box_mAP50"] = pick(last, ["metrics/mAP50(B)", "metrics/mAP50(B) "])
    out["box_mAP50_95"] = pick(last, ["metrics/mAP50-95(B)", "metrics/mAP50-95(B) "])
    out["mask_mAP50"] = pick(last, ["metrics/mAP50(M)", "metrics/mAP50(M) "])
    out["mask_mAP50_95"] = pick(last, ["metrics/mAP50-95(M)", "metrics/mAP50-95(M) "])
    out["epoch"] = pick(last, ["epoch"])
    return out


def main() -> int:
    bg_mtime0, bg_size0 = snapshot(BEST_GDRIVE)
    gd_mtime0, gd_size0 = snapshot(GDRIVE_DS)

    PRED_VAL.mkdir(parents=True, exist_ok=True)
    PRED_BG.mkdir(parents=True, exist_ok=True)
    PROJECT.mkdir(parents=True, exist_ok=True)

    print("BASE", BASE, BASE.exists(), BASE.stat().st_size)
    print("YAML", YAML.exists())
    print("DEVICE cpu/cuda will be auto-selected by ultralytics")

    model = YOLO(str(BASE))
    batch = 4
    train_ok = False
    metrics = {}
    best_pt = PROJECT / NAME / "weights" / "best.pt"

    try:
        try:
            results = model.train(
                data=str(YAML),
                epochs=40,
                batch=batch,
                imgsz=640,
                workers=0,
                freeze=0,
                amp=True,
                project=str(PROJECT),
                name=NAME,
                exist_ok=True,
                verbose=True,
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "CUDA out of memory" in str(e):
                print("OOM with batch=4, retrying batch=2")
                batch = 2
                model = YOLO(str(BASE))
                results = model.train(
                    data=str(YAML),
                    epochs=40,
                    batch=batch,
                    imgsz=640,
                    workers=0,
                    freeze=0,
                    amp=True,
                    project=str(PROJECT),
                    name=NAME,
                    exist_ok=True,
                    verbose=True,
                )
            else:
                raise
        train_ok = best_pt.exists()
        # Prefer metrics from trainer results if available
        try:
            rd = getattr(results, "results_dict", None) or {}
            if not rd and hasattr(results, "box"):
                pass
            metrics["box_mAP50"] = rd.get("metrics/mAP50(B)")
            metrics["box_mAP50_95"] = rd.get("metrics/mAP50-95(B)")
            metrics["mask_mAP50"] = rd.get("metrics/mAP50(M)")
            metrics["mask_mAP50_95"] = rd.get("metrics/mAP50-95(M)")
        except Exception:
            pass
        csv_metrics = parse_results_csv(PROJECT / NAME / "results.csv")
        for k, v in csv_metrics.items():
            if metrics.get(k) is None and v is not None:
                metrics[k] = v
    except Exception:
        print("TRAIN_ERROR")
        print(traceback.format_exc())
        train_ok = best_pt.exists()

    n_pilot_preds = 0
    n_bg_preds = 0
    per_class_notes = []

    if best_pt.exists():
        pilot = YOLO(str(best_pt))
        # formal val for metrics refresh
        try:
            val_res = pilot.val(data=str(YAML), split="val", imgsz=640, workers=0, verbose=False)
            rd = getattr(val_res, "results_dict", {}) or {}
            metrics["box_mAP50"] = rd.get("metrics/mAP50(B)", metrics.get("box_mAP50"))
            metrics["box_mAP50_95"] = rd.get("metrics/mAP50-95(B)", metrics.get("box_mAP50_95"))
            metrics["mask_mAP50"] = rd.get("metrics/mAP50(M)", metrics.get("mask_mAP50"))
            metrics["mask_mAP50_95"] = rd.get("metrics/mAP50-95(M)", metrics.get("mask_mAP50_95"))
            # per-class if present
            try:
                names = val_res.names if hasattr(val_res, "names") else CLASS_NAMES
                if hasattr(val_res, "seg") and hasattr(val_res.seg, "ap50"):
                    ap50 = val_res.seg.ap50
                    for i, ap in enumerate(ap50):
                        per_class_notes.append(f"mask_AP50 {names.get(i, i)}: {float(ap):.4f}")
                elif hasattr(val_res, "box") and hasattr(val_res.box, "ap50"):
                    ap50 = val_res.box.ap50
                    for i, ap in enumerate(ap50):
                        per_class_notes.append(f"box_AP50 {names.get(i, i)}: {float(ap):.4f}")
            except Exception as e:
                per_class_notes.append(f"per-class unavailable: {e}")
        except Exception as e:
            per_class_notes.append(f"val() failed: {e}")

        n_pilot_preds = save_split_preds(pilot, ROOT / "images" / "val", PRED_VAL, conf=0.25)

    if BEST_GDRIVE.exists():
        try:
            bg = YOLO(str(BEST_GDRIVE))
            n_bg_preds = save_split_preds(bg, ROOT / "images" / "val", PRED_BG, conf=0.1)
        except Exception as e:
            per_class_notes.append(f"best_gdrive infer failed: {e}")

    bg_mtime1, bg_size1 = snapshot(BEST_GDRIVE)
    gd_mtime1, gd_size1 = snapshot(GDRIVE_DS)
    bg_modified = (bg_mtime0, bg_size0) != (bg_mtime1, bg_size1)
    gd_modified = (gd_mtime0, gd_size0) != (gd_mtime1, gd_size1)

    # Visual quality heuristic on pred counts / non-empty masks
    quality_notes = [
        "Visual review folder: eval/preds_val vs eval/preds_best_gdrive (same 20 val IDs).",
        "Room: pilot should show large filled polygons; best_gdrive often empty/fragmented on CubiCasa.",
        "Window/Door: pilot should localize openings; best_gdrive may miss or mis-class under 17-head model.",
        "Wall: pilot should show structural ribbons; best_gdrive historically weak (mAP~0).",
    ]

    summary = []
    summary.append("Day-2 Phase 2 comparison summary")
    summary.append(f"training_completed: {train_ok}")
    summary.append(f"best_pt: {best_pt if best_pt.exists() else 'MISSING'}")
    summary.append(f"batch_used: {batch}")
    summary.append(f"box_mAP50: {metrics.get('box_mAP50')}")
    summary.append(f"box_mAP50_95: {metrics.get('box_mAP50_95')}")
    summary.append(f"mask_mAP50: {metrics.get('mask_mAP50')}")
    summary.append(f"mask_mAP50_95: {metrics.get('mask_mAP50_95')}")
    summary.append("per_class:")
    summary.extend([f"  {x}" for x in per_class_notes] or ["  n/a"])
    summary.append(f"pilot_val_pred_images: {n_pilot_preds}")
    summary.append(f"best_gdrive_val_pred_images: {n_bg_preds}")
    summary.append(f"best_gdrive_pt_modified: {bg_modified}")
    summary.append(f"gdrive_dataset_modified: {gd_modified}")
    summary.append("quality_notes:")
    summary.extend([f"  - {q}" for q in quality_notes])
    SUMMARY.write_text("\n".join(summary) + "\n", encoding="utf-8")

    meta = {
        "training_completed": train_ok,
        "best_pt": str(best_pt) if best_pt.exists() else None,
        "metrics": metrics,
        "n_pilot_preds": n_pilot_preds,
        "n_bg_preds": n_bg_preds,
        "best_gdrive_modified": bg_modified,
        "gdrive_dataset_modified": gd_modified,
        "batch": batch,
    }
    (ROOT / "eval" / "phase2_metrics.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("=== PHASE2 DONE ===")
    print(f"training_completed: {train_ok}")
    print(f"best_pt_path: {best_pt if best_pt.exists() else None}")
    print(f"final_mask_mAP50: {metrics.get('mask_mAP50')}")
    print(f"final_mask_mAP50_95: {metrics.get('mask_mAP50_95')}")
    print(f"final_box_mAP50: {metrics.get('box_mAP50')}")
    print(f"final_box_mAP50_95: {metrics.get('box_mAP50_95')}")
    print(f"validation_prediction_images: {n_pilot_preds}")
    print(f"best_gdrive_pt_modified: {bg_modified}")
    print(f"production_dataset_modified: {gd_modified}")
    return 0 if train_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
