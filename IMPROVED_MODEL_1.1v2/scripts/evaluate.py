#!/usr/bin/env python3
"""Evaluate YOLO11 segmentation model — per-class mAP and optional legacy comparison."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dataset_tools.yolo_labels import CLASS_NAMES  # noqa: E402


def extract_seg_metrics(metrics) -> dict:
    """Pull mask metrics from Ultralytics validation results."""
    out: dict = {
        "overall": {},
        "per_class": {},
    }
    box = getattr(metrics, "box", None)
    seg = getattr(metrics, "seg", None)

    if seg is not None:
        out["overall"]["map50"] = float(getattr(seg, "map50", 0.0) or 0.0)
        out["overall"]["map50_95"] = float(getattr(seg, "map", 0.0) or 0.0)
        maps = getattr(seg, "maps", None)
        if maps is not None:
            for idx, name in CLASS_NAMES.items():
                if idx < len(maps):
                    out["per_class"][name] = {"map50_95": float(maps[idx])}
    elif box is not None:
        out["overall"]["map50"] = float(getattr(box, "map50", 0.0) or 0.0)
        out["overall"]["map50_95"] = float(getattr(box, "map", 0.0) or 0.0)

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate YOLO11-seg on val set.")
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help="Path to best.pt",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "prototype_7_batch" / "dataset.yaml",
    )
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--device", default="")
    parser.add_argument(
        "--compare-legacy",
        type=Path,
        default=None,
        help="Optional legacy web_file weights for side-by-side val metrics",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed.", file=sys.stderr)
        return 1

    data_yaml = args.data.resolve()
    if not data_yaml.is_file():
        print(f"ERROR: dataset.yaml not found: {data_yaml}", file=sys.stderr)
        return 1

    report: dict = {"data": str(data_yaml), "models": {}}

    def eval_model(label: str, weights: Path) -> None:
        model = YOLO(str(weights))
        kwargs = {"data": str(data_yaml), "imgsz": args.imgsz, "split": "val"}
        if args.device:
            kwargs["device"] = args.device
        metrics = model.val(**kwargs)
        report["models"][label] = extract_seg_metrics(metrics)

    eval_model("improved", args.weights.resolve())
    if args.compare_legacy:
        eval_model("legacy", args.compare_legacy.resolve())

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}")
    else:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
