#!/usr/bin/env python3
"""Split a flat image batch into train/val folders using manifest.csv ranks."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_BATCH = PROJECT_ROOT / "data" / "prototype_7_batch"
DEFAULT_MANIFEST = DEFAULT_BATCH / "manifest.csv"
TRAIN_MAX_RANK = 20


def load_manifest(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_batch(
    batch_root: Path,
    manifest_path: Path,
    *,
    train_max_rank: int = TRAIN_MAX_RANK,
    source_images: Path | None = None,
) -> dict[str, list[str]]:
    """Copy images into images/train and images/val based on manifest rank."""
    rows = load_manifest(manifest_path)
    if not rows:
        raise ValueError(f"Empty manifest: {manifest_path}")

    flat_dir = source_images or (batch_root / "images")
    if not flat_dir.is_dir():
        raise FileNotFoundError(f"Source images directory not found: {flat_dir}")

    train_dir = batch_root / "images" / "train"
    val_dir = batch_root / "images" / "val"
    labels_train = batch_root / "labels" / "train"
    labels_val = batch_root / "labels" / "val"

    for directory in (train_dir, val_dir, labels_train, labels_val):
        directory.mkdir(parents=True, exist_ok=True)

    train_files: list[str] = []
    val_files: list[str] = []

    for row in rows:
        filename = row["filename"]
        rank = int(row["rank"])
        split = "train" if rank <= train_max_rank else "val"
        src = flat_dir / filename
        if not src.is_file():
            src = batch_root / "images" / filename
        if not src.is_file():
            raise FileNotFoundError(f"Image not found for manifest entry: {filename}")

        dest_root = train_dir if split == "train" else val_dir
        shutil.copy2(src, dest_root / filename)
        (train_files if split == "train" else val_files).append(filename)

    summary = {
        "batch_root": str(batch_root),
        "manifest": str(manifest_path),
        "train_max_rank": train_max_rank,
        "train_count": len(train_files),
        "val_count": len(val_files),
        "train": train_files,
        "val": val_files,
    }
    (batch_root / "split_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def bootstrap_from_legacy_batch(
    batch_root: Path,
    legacy_flat: Path,
    legacy_manifest: Path,
) -> None:
    """Copy flat images + manifest from prototype_11_batch into prototype_7_batch."""
    batch_root.mkdir(parents=True, exist_ok=True)
    images_flat = batch_root / "images"
    images_flat.mkdir(parents=True, exist_ok=True)

    for jpg in legacy_flat.glob("*.jpg"):
        shutil.copy2(jpg, images_flat / jpg.name)

    shutil.copy2(legacy_manifest, batch_root / "manifest.csv")
    if (legacy_flat.parent / "selection.json").is_file():
        shutil.copy2(legacy_flat.parent / "selection.json", batch_root / "selection.json")


def write_dataset_yaml(batch_root: Path) -> Path:
    """Write Ultralytics dataset.yaml for the 7-class batch."""
    import yaml

    config_path = PROJECT_ROOT / "data" / "prototype_7_classes.yaml"
    with config_path.open(encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    dataset_yaml = {
        "path": str(batch_root.resolve()).replace("\\", "/"),
        "train": cfg["train"],
        "val": cfg["val"],
        "nc": cfg["nc"],
        "names": cfg["names"],
    }
    out = batch_root / "dataset.yaml"
    out.write_text(yaml.dump(dataset_yaml, sort_keys=False), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Split manifest batch into train/val folders.")
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=DEFAULT_BATCH,
        help="Dataset batch root (default: data/prototype_7_batch)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="manifest.csv path (default: <batch-root>/manifest.csv)",
    )
    parser.add_argument(
        "--train-max-rank",
        type=int,
        default=TRAIN_MAX_RANK,
        help="Ranks 1..N go to train; remainder to val (default: 20)",
    )
    parser.add_argument(
        "--bootstrap-from",
        type=Path,
        default=None,
        help="Copy images+manifest from legacy batch (e.g. data/prototype_11_batch)",
    )
    parser.add_argument(
        "--write-dataset-yaml",
        action="store_true",
        help="Write dataset.yaml under batch root",
    )
    args = parser.parse_args()

    batch_root = args.batch_root.resolve()
    manifest_path = args.manifest or (batch_root / "manifest.csv")

    if args.bootstrap_from:
        legacy = args.bootstrap_from.resolve()
        bootstrap_from_legacy_batch(
            batch_root,
            legacy / "images",
            legacy / "manifest.csv",
        )

    if not manifest_path.is_file():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    summary = split_batch(
        batch_root,
        manifest_path,
        train_max_rank=args.train_max_rank,
    )
    print(json.dumps(summary, indent=2))

    if args.write_dataset_yaml:
        yaml_path = write_dataset_yaml(batch_root)
        print(f"Wrote {yaml_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
