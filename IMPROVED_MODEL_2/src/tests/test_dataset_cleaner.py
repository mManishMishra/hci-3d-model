"""Tests for DatasetCleaner."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from dataset_tools.dataset_cleaner import DatasetCleanConfig, DatasetCleaner


def _write_jpg(path: Path, size: tuple[int, int] = (400, 400), color: str = "white") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path, format="JPEG")


def test_deduplicate_by_md5(tmp_path: Path) -> None:
    source = tmp_path / "data"
    source.mkdir()
    _write_jpg(source / "a.jpg", color="white")
    _write_jpg(source / "b.jpg", color="black")

    duplicate = source / "Era"
    duplicate.mkdir()
    _write_jpg(duplicate / "a.jpg")

    config = DatasetCleanConfig(
        source_root=source,
        output_root=tmp_path / "out",
        exclude_subdirs=frozenset({"Era"}),
    )
    report = DatasetCleaner(config).run()

    assert report.original_image_count == 2
    assert report.duplicates_skipped == 0
    assert report.final_image_count == 2
    assert (tmp_path / "out" / "images").is_dir()
    assert len(list((tmp_path / "out" / "images").glob("*.jpg"))) == 2


def test_converts_jfif_to_jpg(tmp_path: Path) -> None:
    source = tmp_path / "data"
    source.mkdir()
    jfif_path = source / "plan.jfif"
    Image.new("RGB", (320, 320), color="blue").save(jfif_path, format="JPEG")

    config = DatasetCleanConfig(
        source_root=source,
        output_root=tmp_path / "out",
        exclude_subdirs=frozenset(),
    )
    report = DatasetCleaner(config).run()

    assert report.final_image_count == 1
    assert report.format_conversions.get("jfif_to_jpg") == 1
    outputs = list((tmp_path / "out" / "images").glob("*.jpg"))
    assert len(outputs) == 1


def test_ignores_pdfs(tmp_path: Path) -> None:
    source = tmp_path / "data"
    source.mkdir()
    _write_jpg(source / "plan.jpg")
    (source / "layout.pdf").write_bytes(b"%PDF-1.4 dummy")

    config = DatasetCleanConfig(
        source_root=source,
        output_root=tmp_path / "out",
        exclude_subdirs=frozenset(),
    )
    report = DatasetCleaner(config).run()

    assert report.pdfs_ignored == 1
    assert report.final_image_count == 1
