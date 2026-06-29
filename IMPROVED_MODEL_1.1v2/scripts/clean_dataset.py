#!/usr/bin/env python3
"""Run DatasetCleaner on the default data → dataset_clean paths."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dataset_tools.dataset_cleaner import DatasetCleanConfig, DatasetCleaner  # noqa: E402


def main() -> int:
    source_root = PROJECT_ROOT / "data"
    output_root = PROJECT_ROOT / "dataset_clean"
    docs_path = PROJECT_ROOT / "docs" / "CLEAN_DATASET_REPORT.md"

    config = DatasetCleanConfig(
        source_root=source_root,
        output_root=output_root,
        exclude_subdirs=frozenset({"Era"}),
        overwrite_output=True,
    )

    cleaner = DatasetCleaner(config)
    report = cleaner.run()

    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(DatasetCleaner.render_markdown_report(report), encoding="utf-8")

    print(f"Source:              {report.source_root}")
    print(f"Output:              {report.images_dir}")
    print(f"Original images:     {report.original_image_count}")
    print(f"Duplicates removed:  {report.duplicates_skipped}")
    print(f"Final image count:   {report.final_image_count}")
    print(f"Report written:      {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
