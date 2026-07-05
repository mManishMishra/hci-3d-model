#!/usr/bin/env python3
"""Train YOLO11 instance segmentation on the locked 7-class floor-plan batch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Train YOLO11n-seg on prototype_7_batch.")
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "prototype_7_batch" / "dataset.yaml",
    )
    parser.add_argument("--model", default="yolo11n-seg.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--device", default="")
    parser.add_argument("--project", default=str(PROJECT_ROOT / "runs"))
    parser.add_argument("--name", default="prototype_7_seg")
    parser.add_argument("--skip-integrity", action="store_true")
    args = parser.parse_args()

    data_yaml = args.data.resolve()
    if not data_yaml.is_file():
        print(f"ERROR: dataset.yaml not found: {data_yaml}", file=sys.stderr)
        return 1

    batch_root = data_yaml.parent
    if not args.skip_integrity:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from check_dataset_integrity import main as integrity_main  # noqa: WPS433

        argv_bak = sys.argv
        sys.argv = ["check_dataset_integrity.py", "--batch-root", str(batch_root)]
        code = integrity_main()
        sys.argv = argv_bak
        if code != 0:
            print(
                "ERROR: dataset integrity check failed. "
                "Export CVAT labels first or pass --skip-integrity for dry runs.",
                file=sys.stderr,
            )
            return code

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. pip install ultralytics>=8.3", file=sys.stderr)
        return 1

    model = YOLO(args.model)
    train_kwargs = {
        "data": str(data_yaml),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "patience": args.patience,
        "project": args.project,
        "name": args.name,
        "mosaic": 1.0,
        "degrees": 5.0,
        "fliplr": 0.5,
    }
    if args.device:
        train_kwargs["device"] = args.device

    results = model.train(**train_kwargs)
    print(f"Training complete. Best weights: {results.save_dir / 'weights' / 'best.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
