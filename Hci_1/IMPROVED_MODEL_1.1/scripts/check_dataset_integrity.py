#!/usr/bin/env python3
"""End-to-end dataset integrity checks for the 7-class YOLO11 batch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dataset_tools.yolo_labels import CLASS_NAMES, NC  # noqa: E402

try:
    from validate_labels import validate_split
except ImportError:
    from scripts.validate_labels import validate_split  # type: ignore


def check_dataset_yaml(batch_root: Path) -> list[str]:
    errors: list[str] = []
    yaml_path = batch_root / "dataset.yaml"
    if not yaml_path.is_file():
        errors.append(f"missing dataset.yaml: {yaml_path}")
        return errors

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    for key in ("path", "train", "val", "nc", "names"):
        if key not in data:
            errors.append(f"dataset.yaml missing key: {key}")

    if data.get("nc") != NC:
        errors.append(f"dataset.yaml nc={data.get('nc')} expected {NC}")

    names = data.get("names", {})
    for idx, expected in CLASS_NAMES.items():
        actual = names.get(idx) if isinstance(names, dict) else None
        if str(actual) != expected:
            errors.append(f"dataset.yaml names[{idx}]={actual!r} expected {expected!r}")

    train_path = batch_root / data.get("train", "images/train")
    val_path = batch_root / data.get("val", "images/val")
    if train_path.resolve() == val_path.resolve():
        errors.append("dataset.yaml train and val must not be the same path")

    if not train_path.is_dir():
        errors.append(f"train images missing: {train_path}")
    if not val_path.is_dir():
        errors.append(f"val images missing: {val_path}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 7-class dataset integrity.")
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "prototype_7_batch",
    )
    parser.add_argument("--allow-empty-labels", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    batch_root = args.batch_root.resolve()
    report: dict = {
        "batch_root": str(batch_root),
        "yaml_errors": check_dataset_yaml(batch_root),
        "train": validate_split(
            batch_root / "images" / "train",
            batch_root / "labels" / "train",
            allow_empty_labels=args.allow_empty_labels,
        ),
        "val": validate_split(
            batch_root / "images" / "val",
            batch_root / "labels" / "val",
            allow_empty_labels=args.allow_empty_labels,
        ),
    }
    report["ok"] = (
        not report["yaml_errors"]
        and report["train"]["ok"]
        and report["val"]["ok"]
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Dataset integrity: {'PASS' if report['ok'] else 'FAIL'}")
        for err in report["yaml_errors"]:
            print(f"  YAML ERROR: {err}")
        for split in ("train", "val"):
            part = report[split]
            print(
                f"  {split}: {'OK' if part['ok'] else 'FAIL'} "
                f"(images={part['images_checked']}, instances={part['instances']})"
            )

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
