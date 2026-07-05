#!/usr/bin/env python3
"""
Map CVAT YOLO 1.1 segmentation export to locked 7-class IDs (0–6).

CVAT may export labels with alphabetical class ordering. This script remaps
label files by matching obj.names / classes.txt or by validating existing IDs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dataset_tools.yolo_labels import (  # noqa: E402
    CLASS_NAMES,
    NAME_TO_ID,
    NC,
    class_id_from_name,
    parse_yolo_seg_line,
    validate_label_file,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_cvat_class_order(names_file: Path) -> dict[int, int]:
    """
    Build mapping from CVAT-exported class index → locked 7-class ID.

    names_file lines are in CVAT export order (0..nc-1 per line name).
    """
    lines = [
        line.strip()
        for line in names_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    mapping: dict[int, int] = {}
    for cvat_idx, raw_name in enumerate(lines):
        locked_id = class_id_from_name(raw_name)
        if locked_id is None:
            raise ValueError(f"Unknown CVAT class name {raw_name!r} in {names_file}")
        mapping[cvat_idx] = locked_id
    return mapping


def remap_label_lines(text: str, id_map: dict[int, int] | None) -> tuple[str, list[str]]:
    errors: list[str] = []
    out_lines: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        class_id, coords, line_errors = parse_yolo_seg_line(stripped, line_no)
        errors.extend(line_errors)
        if line_errors:
            continue
        new_id = id_map.get(class_id, class_id) if id_map else class_id
        if new_id not in CLASS_NAMES:
            errors.append(f"line {line_no}: remapped id {new_id} not in 0..{NC - 1}")
            continue
        coord_str = " ".join(f"{c:.6f}" for c in coords)
        out_lines.append(f"{new_id} {coord_str}")
    return "\n".join(out_lines) + ("\n" if out_lines else ""), errors


def copy_split(
    export_dir: Path,
    batch_root: Path,
    *,
    id_map: dict[int, int] | None,
    split_subdirs: bool = True,
) -> dict:
    """
    Import CVAT export into batch_root labels.

    Supports:
      - export_dir/train/*.txt + images
      - export_dir/labels/train/*.txt
    """
    report: dict = {"copied": 0, "errors": [], "splits": {}}

    for split in ("train", "val"):
        candidates = [
            export_dir / split,
            export_dir / "labels" / split,
            export_dir / "obj_train_data" if split == "train" else export_dir / "obj_val_data",
        ]
        src_labels = next((c for c in candidates if c.is_dir()), None)
        if src_labels is None:
            continue

        dest_labels = batch_root / "labels" / split
        dest_labels.mkdir(parents=True, exist_ok=True)
        split_report = {"files": 0, "errors": []}

        for txt in sorted(src_labels.glob("*.txt")):
            if txt.name in {"classes.txt", "obj.names"}:
                continue
            raw = txt.read_text(encoding="utf-8")
            remapped, errors = remap_label_lines(raw, id_map)
            split_report["errors"].extend(errors)
            (dest_labels / txt.name).write_text(remapped, encoding="utf-8")
            split_report["files"] += 1

        report["splits"][split] = split_report
        report["copied"] += split_report["files"]
        report["errors"].extend(split_report["errors"])

    if not split_subdirs:
        flat_labels = export_dir / "labels"
        if flat_labels.is_dir():
            for txt in flat_labels.glob("*.txt"):
                remapped, errors = remap_label_lines(txt.read_text(encoding="utf-8"), id_map)
                report["errors"].extend(errors)
                # Caller must place into train/val manually if flat
                (batch_root / "labels" / "train" / txt.name).write_text(remapped, encoding="utf-8")
                report["copied"] += 1

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Import CVAT YOLO-seg export into 7-class batch.")
    parser.add_argument("export_dir", type=Path, help="CVAT YOLO 1.1 export directory")
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "prototype_7_batch",
    )
    parser.add_argument(
        "--names-file",
        type=Path,
        default=None,
        help="obj.names or classes.txt from CVAT export (for ID remap)",
    )
    parser.add_argument("--validate", action="store_true", help="Run validate_labels after import")
    args = parser.parse_args()

    export_dir = args.export_dir.resolve()
    batch_root = args.batch_root.resolve()

    id_map: dict[int, int] | None = None
    names_file = args.names_file
    if names_file is None:
        for candidate in (
            export_dir / "obj.names",
            export_dir / "classes.txt",
            export_dir / "train" / "classes.txt",
        ):
            if candidate.is_file():
                names_file = candidate
                break

    if names_file and names_file.is_file():
        id_map = load_cvat_class_order(names_file)
        print(f"Using CVAT class remap from {names_file}: {id_map}")

    report = copy_split(export_dir, batch_root, id_map=id_map)
    print(json.dumps(report, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
