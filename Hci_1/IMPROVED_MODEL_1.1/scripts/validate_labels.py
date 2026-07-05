#!/usr/bin/env python3
"""Validate YOLO 1.1 segmentation labels for the locked 7-class taxonomy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dataset_tools.yolo_labels import NC, CLASS_NAMES, validate_label_file  # noqa: E402

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def find_images(images_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(images_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(path)
    return files


def validate_split(
    images_dir: Path,
    labels_dir: Path,
    *,
    allow_empty_labels: bool = False,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0
    instances = 0

    if not images_dir.is_dir():
        errors.append(f"missing images directory: {images_dir}")
        return {"ok": False, "errors": errors, "warnings": warnings}

    labels_dir.mkdir(parents=True, exist_ok=True)

    for image_path in find_images(images_dir):
        label_path = labels_dir / f"{image_path.stem}.txt"
        checked += 1
        if not label_path.is_file():
            msg = f"missing label for image: {image_path.name}"
            if allow_empty_labels:
                warnings.append(msg)
            else:
                errors.append(msg)
            continue
        result = validate_label_file(label_path, allow_empty=allow_empty_labels)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
        instances += result.instance_count

    orphan_labels = []
    for label_path in sorted(labels_dir.glob("*.txt")):
        if not any(
            image_path.stem == label_path.stem for image_path in find_images(images_dir)
        ):
            orphan_labels.append(label_path.name)

    for name in orphan_labels:
        warnings.append(f"orphan label without image: {name}")

    ok = not errors
    return {
        "ok": ok,
        "images_checked": checked,
        "instances": instances,
        "errors": errors,
        "warnings": warnings,
        "nc": NC,
        "class_names": CLASS_NAMES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate YOLO-seg labels (7 classes).")
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "prototype_7_batch",
    )
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    batch_root = args.batch_root.resolve()
    report = {
        "batch_root": str(batch_root),
        "train": validate_split(
            batch_root / "images" / "train",
            batch_root / "labels" / "train",
            allow_empty_labels=args.allow_empty,
        ),
        "val": validate_split(
            batch_root / "images" / "val",
            batch_root / "labels" / "val",
            allow_empty_labels=args.allow_empty,
        ),
    }
    report["ok"] = report["train"]["ok"] and report["val"]["ok"]

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Batch: {batch_root}")
        for split in ("train", "val"):
            part = report[split]
            status = "OK" if part["ok"] else "FAIL"
            print(f"  {split}: {status} — images={part['images_checked']} instances={part['instances']}")
            for err in part["errors"][:20]:
                print(f"    ERROR: {err}")
            if len(part["errors"]) > 20:
                print(f"    ... and {len(part['errors']) - 20} more errors")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
