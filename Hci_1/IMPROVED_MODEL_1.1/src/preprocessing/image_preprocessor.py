"""
Floor plan image preprocessing.

Normalizes input rasters (JPG, PNG, JFIF, GIF) into a consistent format
suitable for downstream detection and graph extraction models.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import cv2
import numpy as np
from PIL import Image, ImageOps

RASTER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".jfif", ".png", ".gif"})


class InputFormat(str, Enum):
    """Detected input file format."""

    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    JFIF = "jfif"
    UNKNOWN = "unknown"


_FORMAT_BY_EXT: dict[str, InputFormat] = {
    ".jpg": InputFormat.JPEG,
    ".jpeg": InputFormat.JPEG,
    ".jfif": InputFormat.JFIF,
    ".png": InputFormat.PNG,
    ".gif": InputFormat.GIF,
}


@dataclass(frozen=True)
class PreprocessConfig:
    """Configuration for the preprocessing pipeline."""

    long_edge_px: int = 1280
    deskew_enabled: bool = True
    preserve_aspect_ratio: bool = True
    adaptive_block_size: int = 11
    adaptive_c: int = 2
    denoise_kernel: int = 3
    morph_kernel: int = 2
    min_deskew_pixels: int = 100


@dataclass(frozen=True)
class PreprocessedImage:
    """
    Result of preprocessing a single floor plan image.

    Attributes:
        image_path: Original source file path.
        original_width: Source image width in pixels.
        original_height: Source image height in pixels.
        processed_image: Preprocessed HxW or HxWx3 uint8 array.
        metadata: Preprocessing provenance and step parameters.
    """

    image_path: Path
    original_width: int
    original_height: int
    processed_image: np.ndarray
    metadata: dict[str, Any]


@runtime_checkable
class ImageLoader(Protocol):
    """Protocol for format-specific image loaders."""

    def supports(self, path: Path) -> bool:
        """Return True if this loader handles the given path."""
        ...

    def load(self, path: Path) -> np.ndarray:
        """Load image as BGR uint8 numpy array."""
        ...


class ImagePreprocessor:
    """
    Normalize floor plan images for the detection and graph pipeline.

    Pipeline stages:
        1. Load raster (JPG, PNG, JFIF, GIF)
        2. Grayscale conversion
        3. Optional deskew correction
        4. Median denoising
        5. Adaptive thresholding
        6. Morphological noise removal
        7. Intensity normalization
        8. Resize to target long edge

    Example:
        >>> preprocessor = ImagePreprocessor(PreprocessConfig(long_edge_px=1280))
        >>> result = preprocessor.process(Path("plan.jpg"))
        >>> result.processed_image.ndim in (2, 3)
    """

    def __init__(self, config: PreprocessConfig | None = None) -> None:
        self._config = config or PreprocessConfig()

    @property
    def config(self) -> PreprocessConfig:
        return self._config

    def process(self, source_path: Path) -> PreprocessedImage:
        """
        Run the full preprocessing pipeline on a single image.

        Args:
            source_path: Path to input floor plan image.

        Returns:
            PreprocessedImage with normalized array and metadata.

        Raises:
            FileNotFoundError: If source_path does not exist.
            ValueError: If the file format is unsupported or image is corrupt.
        """
        path = Path(source_path)
        if not path.is_file():
            raise FileNotFoundError(f"Source image does not exist: {path}")

        source_format = self.detect_format(path)
        if source_format == InputFormat.UNKNOWN:
            raise ValueError(f"Unsupported image format: {path.suffix}")

        bgr = self.load(path)
        if bgr is None or bgr.size == 0:
            raise ValueError(f"Could not read image or image is empty: {path}")

        original_height, original_width = bgr.shape[:2]
        metadata: dict[str, Any] = {
            "source_format": source_format.value,
            "steps": [],
        }

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        metadata["steps"].append("grayscale")

        deskew_angle = 0.0
        if self._config.deskew_enabled:
            gray, deskew_angle = self.deskew(gray)
            metadata["steps"].append("deskew")
            metadata["deskew_angle_deg"] = deskew_angle

        gray = self._denoise(gray)
        metadata["steps"].append("denoise")

        binary = self.binarize(gray)
        metadata["steps"].append("adaptive_threshold")

        binary = self._remove_morph_noise(binary)
        metadata["steps"].append("morph_noise_removal")

        normalized = self.normalize(binary)
        metadata["steps"].append("normalize")

        resized = self.resize(normalized)
        metadata["steps"].append("resize")
        metadata["output_width"] = int(resized.shape[1])
        metadata["output_height"] = int(resized.shape[0])
        metadata["long_edge_px"] = self._config.long_edge_px

        processed = self._to_bgr(resized)

        return PreprocessedImage(
            image_path=path.resolve(),
            original_width=original_width,
            original_height=original_height,
            processed_image=processed,
            metadata=metadata,
        )

    def detect_format(self, path: Path) -> InputFormat:
        """Detect input format from extension and file header."""
        ext = path.suffix.lower()
        if ext not in RASTER_EXTENSIONS:
            return InputFormat.UNKNOWN

        header = path.read_bytes()[:12]
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return InputFormat.PNG
        if header[:3] == b"GIF":
            return InputFormat.GIF
        if header[:2] == b"\xff\xd8":
            return InputFormat.JPEG if ext != ".jfif" else InputFormat.JFIF

        return _FORMAT_BY_EXT.get(ext, InputFormat.UNKNOWN)

    def load(self, path: Path) -> np.ndarray:
        """Load raw image as BGR uint8 array without enhancement."""
        ext = path.suffix.lower()
        if ext in {".gif", ".jfif"}:
            return self._load_with_pil(path, first_frame_only=ext == ".gif")

        data = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if image is None:
            return self._load_with_pil(path, first_frame_only=False)
        return image

    def deskew(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Correct minor rotation skew using minimum-area bounding rectangle.

        Returns:
            Tuple of (corrected_image, angle_degrees).
        """
        if image.ndim == 3:
            work = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            work = image

        inverted = cv2.bitwise_not(work)
        coords = np.column_stack(np.where(inverted > 0))
        if len(coords) < self._config.min_deskew_pixels:
            return image, 0.0

        rect = cv2.minAreaRect(coords.astype(np.float32))
        angle = float(rect[-1])
        if angle < -45.0:
            angle = 90.0 + angle
        elif angle > 45.0:
            angle = angle - 90.0

        if abs(angle) < 0.1:
            return image, 0.0

        h, w = work.shape[:2]
        center = (w / 2.0, h / 2.0)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, angle

    def resize(self, image: np.ndarray) -> np.ndarray:
        """Resize image so long edge equals config.long_edge_px."""
        h, w = image.shape[:2]
        long_edge = max(h, w)
        target = self._config.long_edge_px

        if long_edge == target:
            return image

        scale = target / float(long_edge)
        if self._config.preserve_aspect_ratio:
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
        else:
            new_w = target
            new_h = target

        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        return cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    def binarize(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive Gaussian thresholding for line extraction."""
        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        block = self._config.adaptive_block_size
        if block % 2 == 0:
            block += 1
        block = max(3, block)

        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block,
            self._config.adaptive_c,
        )

    def normalize(self, image: np.ndarray) -> np.ndarray:
        """Normalize pixel intensities to full uint8 range."""
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)

    def save_debug(self, result: PreprocessedImage, output_path: Path) -> None:
        """Write preprocessed image to disk for pipeline debugging."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = result.processed_image
        if not cv2.imwrite(str(output_path), image):
            raise OSError(f"Failed to write preprocessed image: {output_path}")

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        kernel = self._config.denoise_kernel
        if kernel % 2 == 0:
            kernel += 1
        if kernel < 3:
            return image
        return cv2.medianBlur(image, kernel)

    def _remove_morph_noise(self, image: np.ndarray) -> np.ndarray:
        k = max(1, self._config.morph_kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)

    @staticmethod
    def _to_bgr(image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image

    @staticmethod
    def _load_with_pil(path: Path, *, first_frame_only: bool) -> np.ndarray:
        with Image.open(path) as pil_image:
            pil_image = ImageOps.exif_transpose(pil_image)
            if first_frame_only:
                pil_image.seek(0)
            rgb = pil_image.convert("RGB")
        array = np.array(rgb, dtype=np.uint8)
        return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)

    @staticmethod
    def content_hash(path: Path) -> str:
        """Return stable SHA-256 hex digest for a file."""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
