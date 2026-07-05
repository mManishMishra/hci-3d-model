"""Tests for YOLO label validation."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.yolo_labels import validate_label_file


def test_valid_label_line(tmp_path: Path) -> None:
    label = tmp_path / "sample.txt"
    label.write_text("0 0.1 0.1 0.2 0.1 0.2 0.2 0.1 0.2\n", encoding="utf-8")
    result = validate_label_file(label)
    assert result.ok
    assert result.instance_count == 1


def test_invalid_class_id(tmp_path: Path) -> None:
    label = tmp_path / "bad.txt"
    label.write_text("9 0.1 0.1 0.2 0.1 0.2 0.2 0.1 0.2\n", encoding="utf-8")
    result = validate_label_file(label)
    assert not result.ok
