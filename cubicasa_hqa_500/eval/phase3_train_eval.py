#!/usr/bin/env python3
"""Phase 3: offline YOLO train on cubicasa_hqa_500 + compare. No production writes."""
from __future__ import annotations

import csv
import json
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(r"D:\HCI_interor\cubicasa_hqa_500")
YAML = ROOT / "dataset.yaml"
BASE = Path(r"D:\HCI_interor\yolov8n-seg.pt")
PILOT_BEST = Path(
    r"D:\HCI_interor\cubicasa_pilot_100_trainset\runs\pilot100_offline\weights\best.pt"
)
BEST_GDRIVE = Path(r"D:\HCI_interor\best_gdrive.pt")
GDRIVE_DS = Path(r"D:\HCI_interor\gdrive_dataset")
HCI = Path(r"D:\HCI_interor\Hci_1")
PROJECT = ROOT / "runs"
NAME = "hqa500_offline"
PRED_VAL = ROOT / "eval" / "preds_val"
COMPARE = ROOT / "eval" / "compare"
SUMMARY = ROOT / "eval" / "comparison_summary.txt"
NAMES = {0: "Room", 1: "Window", 2: "Door", 3: "Wall"}
COLORS = {
    0: (255, 0, 0),
    1: (255, 0, 255),
    2: (0, 165, 255),
    3: (0, 200, 0),
}


def snap(p: Path):
    if not p.exists():
        return None, None
    st = p.stat()
    return st.st_mtime, st.st_size


def preflight():
    errs = []
    n_ti = len(list((ROOT / "images" / "train").glob("*.png")))
    n_tl = len(list((ROOT / "labels" / "train").glob("*.txt")))
    n_vi = len(list((ROOT / "images" / "val").glob("*.png")))
    n_vl = len(list((ROOT / "labels" / "val").glob("*.txt")))
    print(f"preflight train_img={n_ti} train_lbl={n_tl} val_img={n_vi} val_lbl={n_vl}")
    if n_ti != 500 or n_tl != 500:
        errs.append(f"train counts {n_ti}/{n_tl}")
    if n_vi != 245 or n_vl != 245:
        errs.append(f"val counts {n_vi}/{n_vl}")
    for p, label in [
        (YAML, "yaml"),
        (BASE, "base"),
        (PILOT_BEST, "pilot_best"),
        (BEST_GDRIVE, "best_gdrive"),
    ]:
        ok = p.exists()
        print(f"preflight {label}: {ok} ({p})")
        if not ok:
            errs.append(f"missing {label}")
    # pairing
    ti = {p.stem for p in (ROOT / "images" / "train").glob("*.png")}
    tl = {p.stem for p in (ROOT / "labels" / "train").glob("*.txt")}
    vi = {p.stem for p in (ROOT / "images" / "val").glob("*.png")}
    vl = {p.stem for p in (ROOT / "labels" / "val").glob("*.txt")}
    if ti != tl:
        errs.append(f"train unpaired {len(ti ^ tl)}")
    if vi != vl:
        errs.append(f"val unpaired {len(vi ^ vl)}")
    if errs:
        raise RuntimeError("PREFLIGHT FAIL: " + "; ".join(errs))
    print("preflight OK; isolated root only:", ROOT)


def draw_preds(img, result):
    vis = img.copy()
    if result.masks is None or result.boxes is None:
        return vis
    masks = result.masks.data.cpu().numpy()
    cls_ids = result.boxes.cls.cpu().numpy().astype(int)
    h, w = vis.shape[:2]
    for mask, cid in zip(masks, cls_ids):
        color = COLORS.get(int(cid), (128, 128, 128))
        m = cv2.resize(mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
        if not m.any():
            continue
        overlay = vis.copy()
        overlay[m] = color
        vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, color, 2)
    return vis


def save_preds(model: YOLO, out_dir: Path, conf: float, max_n: int | None = None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    imgs = sorted((ROOT / "images" / "val").glob("*.png"))
    if max_n:
        imgs = imgs[:max_n]
    n = 0
    for p in imgs:
        img = cv2.imread(str(p))
        if img is None:
            continue
        r = model.predict(str(p), imgsz=640, conf=conf, verbose=False, save=False)[0]
        cv2.imwrite(str(out_dir / f"{p.stem}_pred.jpg"), draw_preds(img, r))
        n += 1
        if n % 50 == 0:
            print(f"  preds {n}/{len(imgs)}")
    return n


def run_val_metrics(model_path: Path, tag: str):
    model = YOLO(str(model_path))
    out = ROOT / "eval" / "_val_tmp" / tag
    out.mkdir(parents=True, exist_ok=True)
    res = model.val(
        data=str(YAML),
        split="val",
        imgsz=640,
        workers=0,
        plots=False,
        save_json=False,
        project=str(out.parent),
        name=tag,
        exist_ok=True,
        verbose=False,
    )
    rd = getattr(res, "results_dict", {}) or {}
    metrics = {
        "box_mAP50": float(rd.get("metrics/mAP50(B)") or 0),
        "box_mAP50_95": float(rd.get("metrics/mAP50-95(B)") or 0),
        "mask_mAP50": float(rd.get("metrics/mAP50(M)") or 0),
        "mask_mAP50_95": float(rd.get("metrics/mAP50-95(M)") or 0),
    }
    per = {}
    try:
        names = res.names if hasattr(res, "names") else NAMES
        if hasattr(res, "seg") and getattr(res.seg, "ap50", None) is not None:
            for i, ap in enumerate(res.seg.ap50):
                per[str(names.get(i, i))] = float(ap)
    except Exception as e:
        per["error"] = str(e)
    return metrics, per, model


def parse_results_csv(csv_path: Path):
    if not csv_path.exists():
        return {}
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    if not rows:
        return {}
    last = rows[-1]

    def pick(*keys):
        for k in keys:
            if k in last and last[k] not in (None, ""):
                try:
                    return float(last[k])
                except ValueError:
                    pass
        return None

    return {
        "box_mAP50": pick("metrics/mAP50(B)"),
        "box_mAP50_95": pick("metrics/mAP50-95(B)"),
        "mask_mAP50": pick("metrics/mAP50(M)"),
        "mask_mAP50_95": pick("metrics/mAP50-95(M)"),
        "epoch": pick("epoch"),
    }


def verdict(metrics, per, pilot_per):
    m50 = metrics.get("mask_mAP50") or 0
    room = per.get("Room") or 0
    win = per.get("Window") or 0
    door = per.get("Door") or 0
    wall = per.get("Wall") or 0
    p_win = pilot_per.get("Window") or 0
    p_door = pilot_per.get("Door") or 0
    p_wall = pilot_per.get("Wall") or 0
    opening_lift = (win > p_win + 0.01) or (door > p_door + 0.01) or (wall > p_wall + 0.01)
    if m50 >= 0.25 and wall >= 0.10 and door >= 0.05 and win >= 0.05 and room >= 0.30:
        return "PASS"
    if m50 >= 0.15 or opening_lift:
        return "PARTIAL"
    return "FAIL"


def main():
    t0 = time.time()
    bg0, gd0, hci0 = snap(BEST_GDRIVE), snap(GDRIVE_DS), snap(HCI)
    PRED_VAL.mkdir(parents=True, exist_ok=True)
    COMPARE.mkdir(parents=True, exist_ok=True)
    PROJECT.mkdir(parents=True, exist_ok=True)

    preflight()

    best_pt = PROJECT / NAME / "weights" / "best.pt"
    train_ok = False
    metrics = {}
    per_class = {}

    print("START TRAIN epochs=60 batch=2 imgsz=640 device=cpu")
    try:
        model = YOLO(str(BASE))
        model.train(
            data=str(YAML),
            epochs=60,
            batch=2,
            imgsz=640,
            freeze=0,
            device="cpu",
            amp=True,
            workers=0,
            project=str(PROJECT),
            name=NAME,
            exist_ok=True,
            verbose=True,
        )
        train_ok = best_pt.exists()
    except Exception:
        print("TRAIN_ERROR")
        print(traceback.format_exc())
        train_ok = best_pt.exists()

    runtime_s = time.time() - t0

    if best_pt.exists():
        metrics, per_class, new_model = run_val_metrics(best_pt, "metrics_new")
        csv_m = parse_results_csv(PROJECT / NAME / "results.csv")
        for k, v in csv_m.items():
            if metrics.get(k) in (None, 0) and v is not None:
                metrics[k] = v
        print("VAL metrics", metrics, per_class)
        n_preds = save_preds(new_model, PRED_VAL, conf=0.25)
        print("preds_val", n_preds)
    else:
        n_preds = 0
        new_model = None

    # Compare models on same val
    pilot_m, pilot_per, pilot_model = {}, {}, None
    gdrive_m, gdrive_per, gdrive_model = {}, {}, None
    try:
        pilot_m, pilot_per, pilot_model = run_val_metrics(PILOT_BEST, "metrics_pilot")
        save_preds(pilot_model, COMPARE / "pilot100", conf=0.25, max_n=50)
    except Exception as e:
        pilot_per = {"error": str(e)}
    try:
        gdrive_m, gdrive_per, gdrive_model = run_val_metrics(BEST_GDRIVE, "metrics_gdrive")
        save_preds(gdrive_model, COMPARE / "best_gdrive", conf=0.10, max_n=50)
    except Exception as e:
        gdrive_per = {"error": str(e)}
    if new_model is not None:
        save_preds(new_model, COMPARE / "hqa500", conf=0.25, max_n=50)

    decision = verdict(metrics, per_class, pilot_per if isinstance(pilot_per, dict) else {})

    # safety
    bg1, gd1, hci1 = snap(BEST_GDRIVE), snap(GDRIVE_DS), snap(HCI)
    untouched = {
        "best_gdrive": bg0 == bg1,
        "gdrive_dataset": gd0 == gd1,
        "Hci_1": hci0 == hci1,
    }

    lines = [
        "Phase 3 HQA-500 comparison summary",
        f"training_completed: {train_ok}",
        f"runtime_seconds: {runtime_s:.1f}",
        f"runtime_hours: {runtime_s/3600:.2f}",
        f"best_pt: {best_pt if best_pt.exists() else 'MISSING'}",
        "",
        "NEW hqa500_offline:",
        f"  mask_mAP50: {metrics.get('mask_mAP50')}",
        f"  mask_mAP50_95: {metrics.get('mask_mAP50_95')}",
        f"  box_mAP50: {metrics.get('box_mAP50')}",
        f"  box_mAP50_95: {metrics.get('box_mAP50_95')}",
        f"  per_class_mask_AP50: {per_class}",
        "",
        "PILOT100:",
        f"  metrics: {pilot_m}",
        f"  per_class: {pilot_per}",
        "",
        "BEST_GDRIVE:",
        f"  metrics: {gdrive_m}",
        f"  per_class: {gdrive_per}",
        "",
        "DELTAS vs pilot100 (mask_mAP50):",
        f"  {(metrics.get('mask_mAP50') or 0) - (pilot_m.get('mask_mAP50') or 0):+.4f}",
        "DELTAS vs best_gdrive (mask_mAP50):",
        f"  {(metrics.get('mask_mAP50') or 0) - (gdrive_m.get('mask_mAP50') or 0):+.4f}",
        "",
        "Visual notes:",
        "  - Compare eval/compare/hqa500 vs pilot100 vs best_gdrive (50-sample subset)",
        "  - Full 245 overlays in eval/preds_val for the new model",
        "  - Expect Room strength first; Wall/Door/Window are the scale-up targets",
        "",
        f"VERDICT: {decision}",
        f"production_untouched: {untouched}",
        "model_promoted: False",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "eval" / "phase3_metrics.json").write_text(
        json.dumps(
            {
                "training_completed": train_ok,
                "runtime_seconds": runtime_s,
                "best_pt": str(best_pt) if best_pt.exists() else None,
                "metrics": metrics,
                "per_class": per_class,
                "pilot": {"metrics": pilot_m, "per_class": pilot_per},
                "gdrive": {"metrics": gdrive_m, "per_class": gdrive_per},
                "verdict": decision,
                "untouched": untouched,
                "n_preds_val": n_preds,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== PHASE3 DONE ===")
    print(f"training_completed: {train_ok}")
    print(f"runtime_seconds: {runtime_s:.1f}")
    print(f"best_pt_path: {best_pt if best_pt.exists() else None}")
    print(f"final_mask_mAP50: {metrics.get('mask_mAP50')}")
    print(f"final_mask_mAP50_95: {metrics.get('mask_mAP50_95')}")
    print(f"final_box_mAP50: {metrics.get('box_mAP50')}")
    print(f"final_box_mAP50_95: {metrics.get('box_mAP50_95')}")
    print(f"per_class: {per_class}")
    print(f"verdict: {decision}")
    print(f"best_gdrive_modified: {not untouched['best_gdrive']}")
    print(f"gdrive_dataset_modified: {not untouched['gdrive_dataset']}")
    print(f"Hci_1_modified: {not untouched['Hci_1']}")
    print("model_promoted: False")
    return 0 if train_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
