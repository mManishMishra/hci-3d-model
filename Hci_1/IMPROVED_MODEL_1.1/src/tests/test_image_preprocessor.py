"""Tests for ImagePreprocessor."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from preprocessing.image_preprocessor import (
    ImagePreprocessor,
    InputFormat,
    PreprocessConfig,
)


def _write_floorplan_jpg(path: Path, size: tuple[int, int] = (640, 480)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((size[1], size[0], 3), 255, dtype=np.uint8)
    cv2.line(image, (40, 40), (size[0] - 40, 40), (0, 0, 0), 3)
    cv2.line(image, (40, 40), (40, size[1] - 40), (0, 0, 0), 3)
    cv2.line(image, (size[0] - 40, 40), (size[0] - 40, size[1] - 40), (0, 0, 0), 3)
    cv2.rectangle(image, (200, 200), (280, 360), (0, 0, 0), 2)
    cv2.imwrite(str(path), image)


def test_detect_format_jpg(tmp_path: Path) -> None:
    path = tmp_path / "plan.jpg"
    _write_floorplan_jpg(path)
    preprocessor = ImagePreprocessor()
    assert preprocessor.detect_format(path) == InputFormat.JPEG


def test_detect_format_png(tmp_path: Path) -> None:
    path = tmp_path / "plan.png"
    _write_floorplan_jpg(path)
    preprocessor = ImagePreprocessor()
    assert preprocessor.detect_format(path) == InputFormat.PNG


def test_load_jfif(tmp_path: Path) -> None:
    path = tmp_path / "plan.jfif"
    Image.new("RGB", (100, 80), color="white").save(path, format="JPEG")
    preprocessor = ImagePreprocessor()
    assert preprocessor.detect_format(path) == InputFormat.JFIF
    array = preprocessor.load(path)
    assert array.shape == (80, 100, 3)


def test_load_gif_first_frame(tmp_path: Path) -> None:
    path = tmp_path / "plan.gif"
    Image.new("RGB", (120, 80), color="white").save(path, save_all=True, append_images=[Image.new("RGB", (120, 80), color="black")], duration=100, loop=0)
    preprocessor = ImagePreprocessor()
    array = preprocessor.load(path)
    assert array.shape == (80, 120, 3)
    assert array.dtype == np.uint8


def test_process_returns_preprocessed_image(tmp_path: Path) -> None:
    path = tmp_path / "plan.jpg"
    _write_floorplan_jpg(path, size=(800, 600))

    config = PreprocessConfig(long_edge_px=400, deskew_enabled=False)
    result = ImagePreprocessor(config).process(path)

    assert result.image_path.resolve() == path.resolve()
    assert result.original_width == 800
    assert result.original_height == 600
    assert result.processed_image.ndim == 3
    assert result.processed_image.dtype == np.uint8
    assert max(result.processed_image.shape[:2]) == 400
    assert "grayscale" in result.metadata["steps"]
    assert "adaptive_threshold" in result.metadata["steps"]
    assert "resize" in result.metadata["steps"]


def test_resize_long_edge(tmp_path: Path) -> None:
    path = tmp_path / "plan.jpg"
    _write_floorplan_jpg(path, size=(1600, 900))

    result = ImagePreprocessor(PreprocessConfig(long_edge_px=640, deskew_enabled=False)).process(path)
    assert max(result.processed_image.shape[:2]) == 640
    assert result.metadata["output_width"] == 640


def test_deskew_rotated_image(tmp_path: Path) -> None:
    path = tmp_path / "plan.jpg"
    _write_floorplan_jpg(path, size=(500, 500))
    source = cv2.imread(str(path))
    center = (250, 250)
    matrix = cv2.getRotationMatrix2D(center, 8.0, 1.0)
    rotated = cv2.warpAffine(source, matrix, (500, 500), borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(str(path), rotated)

    gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
    preprocessor = ImagePreprocessor()
    corrected, angle = preprocessor.deskew(gray)

    assert corrected.shape == gray.shape
    assert abs(angle) > 0.0


def test_save_debug_writes_file(tmp_path: Path) -> None:
    path = tmp_path / "plan.jpg"
    out = tmp_path / "out" / "processed.jpg"
    _write_floorplan_jpg(path)

    preprocessor = ImagePreprocessor(PreprocessConfig(deskew_enabled=False))
    result = preprocessor.process(path)
    preprocessor.save_debug(result, out)

    assert out.is_file()
    written = cv2.imread(str(out))
    assert written is not None
    assert written.shape == result.processed_image.shape


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ImagePreprocessor().process(tmp_path / "missing.jpg")


def test_unsupported_format_raises(tmp_path: Path) -> None:
    path = tmp_path / "plan.pdf"
    path.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="Unsupported"):
        ImagePreprocessor().process(path)
