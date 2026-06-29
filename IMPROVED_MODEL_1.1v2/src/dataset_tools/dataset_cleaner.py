"""
Dataset cleaning utilities — deduplication, format normalization, split creation.

Operates on a source corpus and writes a cleaned copy to a target directory
without modifying the original source tree.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable

from PIL import Image, ImageOps

RASTER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".jfif", ".png", ".gif", ".tif", ".tiff", ".bmp", ".webp"})


class CopyMode(str, Enum):
    """How cleaned files are written to the output directory."""

    COPY = "copy"
    HARDLINK = "hardlink"
    SYMLINK = "symlink"


@dataclass(frozen=True)
class DatasetCleanConfig:
    """Configuration for dataset cleaning and ingest."""

    source_root: Path
    output_root: Path
    exclude_subdirs: frozenset[str] = frozenset({"Era"})
    skip_copy_suffixes: frozenset[str] = frozenset({" (1)"})
    normalize_jfif_to_jpg: bool = True
    extract_gif_first_frame: bool = True
    copy_mode: CopyMode = CopyMode.COPY
    train_ratio: float = 0.70
    val_ratio: float = 0.20
    test_ratio: float = 0.10
    split_seed: int = 42
    min_short_edge_px: int = 256
    overwrite_output: bool = True
    jpeg_quality: int = 95


@dataclass(frozen=True)
class DatasetCleanReport:
    """Summary of a cleaning run."""

    source_root: Path
    output_root: Path
    images_dir: Path
    original_image_count: int
    files_scanned: int
    files_written: int
    duplicates_skipped: int
    pdfs_ignored: int
    excluded_dirs_skipped: int
    copy_suffix_skipped: int
    invalid_skipped: int
    format_conversions: dict[str, int] = field(default_factory=dict)
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def final_image_count(self) -> int:
        return self.files_written


@runtime_checkable
class SplitStrategy(Protocol):
    """Protocol for custom train/val/test assignment strategies."""

    def assign(self, image_paths: list[Path]) -> dict[str, list[Path]]:
        """
        Assign images to splits.

        Returns:
            Dict with keys ``train``, ``val``, ``test`` mapping to path lists.
        """
        ...


class DatasetCleaner:
    """
    Produce a deduplicated, normalized dataset ready for labeling and training.

    Responsibilities:
        - Skip known duplicate subfolders (e.g. ``Era/``)
        - Deduplicate by content hash
        - Normalize JFIF/GIF to JPG
        - Write cleaned images to ``output_root/images/``

    Example:
        >>> config = DatasetCleanConfig(
        ...     source_root=Path("data"),
        ...     output_root=Path("dataset_clean"),
        ... )
        >>> report = DatasetCleaner(config).run()
    """

    def __init__(self, config: DatasetCleanConfig) -> None:
        self._config = config

    @property
    def config(self) -> DatasetCleanConfig:
        return self._config

    @property
    def images_dir(self) -> Path:
        return self._config.output_root / "images"

    def run(self) -> DatasetCleanReport:
        """
        Execute deduplication and format normalization.

        Returns:
            DatasetCleanReport summarizing actions taken.
        """
        source_root = self._config.source_root.resolve()
        output_root = self._config.output_root.resolve()
        images_dir = output_root / "images"

        if not source_root.is_dir():
            raise FileNotFoundError(f"Source root does not exist: {source_root}")

        if output_root.exists():
            if not self._config.overwrite_output:
                raise FileExistsError(f"Output root already exists: {output_root}")
            if images_dir.exists():
                shutil.rmtree(images_dir)

        images_dir.mkdir(parents=True, exist_ok=True)

        raster_paths, pdfs_ignored, excluded_dirs_skipped = self._collect_raster_paths(source_root)
        original_image_count = len(raster_paths)

        canonical_paths, copy_suffix_skipped = self._filter_copy_suffix_duplicates(raster_paths)
        unique_paths = self.deduplicate(canonical_paths)
        duplicates_skipped = len(canonical_paths) - len(unique_paths)

        format_conversions: dict[str, int] = {}
        errors: list[str] = []
        invalid_skipped = 0
        files_written = 0
        used_names: set[str] = set()

        for source_path in unique_paths:
            try:
                if not self._is_valid_raster(source_path):
                    invalid_skipped += 1
                    errors.append(f"Invalid or unreadable raster: {source_path}")
                    continue

                dest_name = self._unique_output_name(source_path, used_names)
                dest_path = images_dir / dest_name
                src_ext = source_path.suffix.lower()
                self.normalize_image(source_path, dest_path)

                if src_ext in {".jfif", ".gif"}:
                    key = f"{src_ext.lstrip('.')}_to_jpg"
                    format_conversions[key] = format_conversions.get(key, 0) + 1
                elif src_ext in {".png", ".tif", ".tiff", ".bmp", ".webp"}:
                    key = f"{src_ext.lstrip('.')}_to_jpg"
                    format_conversions[key] = format_conversions.get(key, 0) + 1

                files_written += 1
            except Exception as exc:
                invalid_skipped += 1
                errors.append(f"{source_path}: {exc}")

        return DatasetCleanReport(
            source_root=source_root,
            output_root=output_root,
            images_dir=images_dir,
            original_image_count=original_image_count,
            files_scanned=len(raster_paths),
            files_written=files_written,
            duplicates_skipped=duplicates_skipped,
            pdfs_ignored=pdfs_ignored,
            excluded_dirs_skipped=excluded_dirs_skipped,
            copy_suffix_skipped=copy_suffix_skipped,
            invalid_skipped=invalid_skipped,
            format_conversions=format_conversions,
            errors=tuple(errors),
        )

    def _collect_raster_paths(
        self, source_root: Path
    ) -> tuple[list[Path], int, int]:
        """Collect raster image paths; count ignored PDFs and excluded-dir files."""
        raster_paths: list[Path] = []
        pdfs_ignored = 0
        excluded_dirs_skipped = 0

        for path in sorted(source_root.rglob("*")):
            if not path.is_file():
                continue

            if self._is_in_excluded_subdir(path, source_root):
                excluded_dirs_skipped += 1
                continue

            ext = path.suffix.lower()
            if ext == ".pdf":
                pdfs_ignored += 1
                continue

            if ext in RASTER_EXTENSIONS:
                raster_paths.append(path)

        return raster_paths, pdfs_ignored, excluded_dirs_skipped

    def _is_in_excluded_subdir(self, path: Path, source_root: Path) -> bool:
        try:
            rel_parts = path.relative_to(source_root).parts
        except ValueError:
            return True
        if not rel_parts[:-1]:
            return False
        return rel_parts[0] in self._config.exclude_subdirs

    def _filter_copy_suffix_duplicates(
        self, paths: list[Path]
    ) -> tuple[list[Path], int]:
        """Drop ``(1)`` copy files when the base filename exists with identical hash."""
        by_stem_base: dict[str, list[Path]] = {}
        for path in paths:
            base_stem = path.stem
            for suffix in self._config.skip_copy_suffixes:
                if base_stem.endswith(suffix):
                    base_stem = base_stem[: -len(suffix)]
                    break
            key = f"{base_stem.lower()}_{path.suffix.lower()}"
            by_stem_base.setdefault(key, []).append(path)

        kept: list[Path] = []
        copy_suffix_skipped = 0

        for group in by_stem_base.values():
            if len(group) == 1:
                kept.append(group[0])
                continue

            hashes = {self._content_hash(p): p for p in group}
            if len(hashes) == 1:
                canonical = min(group, key=lambda p: self._path_priority(p))
                kept.append(canonical)
                copy_suffix_skipped += len(group) - 1
            else:
                kept.extend(group)

        return sorted(kept, key=lambda p: self._path_priority(p)), copy_suffix_skipped

    def deduplicate(self, paths: list[Path]) -> list[Path]:
        """Return canonical paths after content-hash deduplication."""
        sorted_paths = sorted(paths, key=lambda p: self._path_priority(p))
        seen_hashes: dict[str, Path] = {}

        for path in sorted_paths:
            digest = self._content_hash(path)
            if digest not in seen_hashes:
                seen_hashes[digest] = path

        return list(seen_hashes.values())

    def normalize_image(self, source: Path, dest: Path) -> None:
        """Convert source raster to JPG at dest."""
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            if source.suffix.lower() == ".gif" and self._config.extract_gif_first_frame:
                image.seek(0)
            rgb = image.convert("RGB")
            short_edge = min(rgb.size)
            if short_edge < self._config.min_short_edge_px:
                raise ValueError(
                    f"Image short edge {short_edge}px below minimum "
                    f"{self._config.min_short_edge_px}px"
                )
            rgb.save(dest, format="JPEG", quality=self._config.jpeg_quality, optimize=True)

    def _is_valid_raster(self, path: Path) -> bool:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.load()
                return min(image.size) >= self._config.min_short_edge_px
        except Exception:
            return False

    def _content_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _path_priority(self, path: Path) -> tuple:
        source_root = self._config.source_root.resolve()
        try:
            rel = path.relative_to(source_root)
            depth = len(rel.parts)
        except ValueError:
            depth = 999
        has_copy_suffix = any(
            path.stem.endswith(suffix) for suffix in self._config.skip_copy_suffixes
        )
        return (depth, has_copy_suffix, str(path).lower())

    def _sanitize_stem(self, stem: str) -> str:
        for suffix in self._config.skip_copy_suffixes:
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
        stem = stem.strip().lower()
        stem = re.sub(r"[^\w\-]+", "_", stem)
        stem = re.sub(r"_+", "_", stem).strip("_")
        return stem or "image"

    def _unique_output_name(self, source_path: Path, used_names: set[str]) -> str:
        base = self._sanitize_stem(source_path.stem)
        candidate = f"{base}.jpg"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate

        digest = self._content_hash(source_path)[:8]
        candidate = f"{base}_{digest}.jpg"
        counter = 1
        while candidate in used_names:
            candidate = f"{base}_{digest}_{counter}.jpg"
            counter += 1
        used_names.add(candidate)
        return candidate

    def create_splits(self, image_paths: list[Path]) -> dict[str, list[Path]]:
        """Assign images to train/val/test using configured ratios and split_seed."""
        if not image_paths:
            return {"train": [], "val": [], "test": []}

        ratios = (
            self._config.train_ratio,
            self._config.val_ratio,
            self._config.test_ratio,
        )
        total = sum(ratios)
        if total <= 0:
            raise ValueError("train_ratio + val_ratio + test_ratio must be > 0")

        paths = sorted(image_paths)
        rng = random.Random(self._config.split_seed)
        rng.shuffle(paths)

        n = len(paths)
        n_train = int(n * self._config.train_ratio / total)
        n_val = int(n * self._config.val_ratio / total)
        n_train = min(n_train, n)
        n_val = min(n_val, max(0, n - n_train))

        train = paths[:n_train]
        val = paths[n_train : n_train + n_val]
        test = paths[n_train + n_val :]
        return {"train": train, "val": val, "test": test}

    def write_split_manifest(self, splits: dict[str, list[Path]], manifest_path: Path) -> None:
        """Persist split assignments as JSON manifest."""
        payload = {
            split: [str(p.resolve()) for p in paths]
            for split, paths in splits.items()
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def render_markdown_report(report: DatasetCleanReport) -> str:
        """Render a human-readable Markdown summary of a clean run."""
        conversions = report.format_conversions or {}
        conversion_lines = (
            "\n".join(f"| {k} | {v} |" for k, v in sorted(conversions.items()))
            or "| — | 0 |"
        )
        error_section = ""
        if report.errors:
            sample = "\n".join(f"- {err}" for err in report.errors[:20])
            more = (
                f"\n- … and {len(report.errors) - 20} more"
                if len(report.errors) > 20
                else ""
            )
            error_section = f"\n## Errors / Skipped Files\n\n{sample}{more}\n"

        return f"""# Clean Dataset Report

**Generated by:** `DatasetCleaner`  
**Source:** `{report.source_root}`  
**Output:** `{report.images_dir}`

---

## Summary

| Metric | Count |
|--------|------:|
| **Original image count** (raster files scanned) | {report.original_image_count} |
| **Duplicate count removed** (MD5 deduplication) | {report.duplicates_skipped} |
| **Copy-suffix files skipped** (`(1)` duplicates) | {report.copy_suffix_skipped} |
| **PDFs ignored** | {report.pdfs_ignored} |
| **Invalid / unreadable skipped** | {report.invalid_skipped} |
| **Final image count** | {report.final_image_count} |

---

## Processing Details

| Item | Value |
|------|-------|
| Excluded subdirectories | `Era/` ({report.excluded_dirs_skipped} files skipped in excluded dirs) |
| Output format | JPEG (`.jpg`) |
| Deduplication method | MD5 content hash |
| Train/val/test splits | Not created |

### Format conversions

| Conversion | Count |
|------------|------:|
{conversion_lines}
{error_section}
---

## Output Layout

```
{report.output_root.name}/
└── images/          # {report.final_image_count} deduplicated JPG files
```

---

*End of report*
"""
