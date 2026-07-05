"""Smoke tests — active training pipeline imports only."""

from __future__ import annotations

from dataset_tools.dataset_cleaner import DatasetCleaner, DatasetCleanConfig
from dataset_tools.yolo_labels import CLASS_NAMES, NC, validate_label_file
from preprocessing.image_preprocessor import ImagePreprocessor


def test_package_imports() -> None:
    """Active entry points are importable."""
    assert DatasetCleaner is not None
    assert ImagePreprocessor is not None
    assert validate_label_file is not None


def test_seven_class_taxonomy_locked() -> None:
    """Locked 7-class IDs 0–6."""
    assert NC == 7
    assert CLASS_NAMES[0] == "wall"
    assert CLASS_NAMES[6] == "bathroom"


def test_dataset_cleaner_splits() -> None:
    """create_splits returns train/val/test lists."""
    from pathlib import Path

    paths = [Path(f"img_{i}.jpg") for i in range(10)]
    config = DatasetCleanConfig(
        source_root=Path("data"),
        output_root=Path("out"),
    )
    splits = DatasetCleaner(config).create_splits(paths)
    assert set(splits) == {"train", "val", "test"}
    assert sum(len(v) for v in splits.values()) == 10
