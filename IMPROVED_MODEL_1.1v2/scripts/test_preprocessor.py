#!/usr/bin/env python3
"""Run ImagePreprocessor on a sample floor plan and save debug outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from preprocessing.image_preprocessor import ImagePreprocessor, PreprocessConfig  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "preprocessed"

SEARCH_DIRS = (
    PROJECT_ROOT / "data" / "prototype_dataset" / "images" / "train",
    PROJECT_ROOT / "data" / "prototype_dataset" / "images" / "val",
    PROJECT_ROOT / "data" / "annotation_batch_01",
    PROJECT_ROOT / "dataset_clean" / "images",
    PROJECT_ROOT / "data",
)


def find_sample_image() -> Path | None:
    for directory in SEARCH_DIRS:
        if not directory.is_dir():
            continue
        matches = sorted(directory.rglob("*.jpg"))
        if matches:
            return matches[0]
    return None


def main() -> int:
    sample = find_sample_image()
    if sample is None:
        print("No sample floor plan JPG found under data/ or dataset_clean/.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = PreprocessConfig(long_edge_px=1280, deskew_enabled=True)
    preprocessor = ImagePreprocessor(config)
    result = preprocessor.process(sample)

    stem = sample.stem
    image_out = OUTPUT_DIR / f"{stem}_preprocessed.jpg"
    meta_out = OUTPUT_DIR / f"{stem}_metadata.json"

    preprocessor.save_debug(result, image_out)
    meta_out.write_text(
        json.dumps(
            {
                "image_path": str(result.image_path),
                "original_width": result.original_width,
                "original_height": result.original_height,
                "output_shape": list(result.processed_image.shape),
                "metadata": result.metadata,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Source:     {result.image_path}")
    print(f"Original:   {result.original_width} x {result.original_height}")
    print(f"Output:     {result.metadata['output_width']} x {result.metadata['output_height']}")
    print(f"Image:      {image_out}")
    print(f"Metadata:   {meta_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
