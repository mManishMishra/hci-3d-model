"""YOLO 1.1 segmentation label utilities for the 7-class floor-plan pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Locked 7-class segmentation taxonomy (prototype training IDs 0–6).
CLASS_NAMES: dict[int, str] = {
    0: "wall",
    1: "door",
    2: "window",
    3: "bedroom",
    4: "living_room",
    5: "kitchen",
    6: "bathroom",
}

NAME_TO_ID: dict[str, int] = {name: idx for idx, name in CLASS_NAMES.items()}

# CVAT label names (lowercase) → YOLO ID. Aliases for common variants.
CVAT_NAME_TO_ID: dict[str, int] = {
    **NAME_TO_ID,
    "living room": 4,
    "living-room": 4,
    "livingroom": 4,
}

NC = len(CLASS_NAMES)
MIN_COORD_TOKENS = 6  # 3 points × (x,y)


@dataclass
class LabelValidationResult:
    """Result of validating one label file or a full dataset."""

    label_path: Path | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    instance_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def normalize_class_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def class_id_from_name(name: str) -> int | None:
    key = normalize_class_name(name)
    if key in CVAT_NAME_TO_ID:
        return CVAT_NAME_TO_ID[key]
    return NAME_TO_ID.get(key)


def parse_yolo_seg_line(line: str, line_no: int) -> tuple[int, list[float], list[str]]:
    """Parse one YOLO segmentation line. Returns (class_id, coords, errors)."""
    errors: list[str] = []
    parts = line.strip().split()
    if not parts:
        return -1, [], errors

    try:
        class_id = int(parts[0])
    except ValueError:
        errors.append(f"line {line_no}: invalid class id {parts[0]!r}")
        return -1, [], errors

    if class_id not in CLASS_NAMES:
        errors.append(f"line {line_no}: class_id {class_id} not in 0..{NC - 1}")

    coord_tokens = parts[1:]
    if len(coord_tokens) < MIN_COORD_TOKENS:
        errors.append(
            f"line {line_no}: need >= {MIN_COORD_TOKENS} coordinate tokens, got {len(coord_tokens)}"
        )
        return class_id, [], errors

    if len(coord_tokens) % 2 != 0:
        errors.append(f"line {line_no}: coordinate count must be even")

    coords: list[float] = []
    for i in range(0, len(coord_tokens), 2):
        try:
            x = float(coord_tokens[i])
            y = float(coord_tokens[i + 1])
        except ValueError:
            errors.append(f"line {line_no}: non-numeric coordinate at token {i + 1}")
            continue
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            errors.append(f"line {line_no}: coordinate ({x}, {y}) outside [0, 1]")
        coords.extend([x, y])

    return class_id, coords, errors


def validate_label_file(path: Path, *, allow_empty: bool = False) -> LabelValidationResult:
    """Validate a single YOLO-seg label file."""
    result = LabelValidationResult(label_path=path)
    if not path.is_file():
        result.errors.append(f"missing label file: {path}")
        return result

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        if allow_empty:
            result.warnings.append(f"empty label file: {path}")
            return result
        result.errors.append(f"empty label file: {path}")
        return result

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        _, _, line_errors = parse_yolo_seg_line(stripped, line_no)
        result.errors.extend(line_errors)
        result.instance_count += 1

    return result


def contour_to_yolo_seg(
    points: list[tuple[float, float]], img_w: int, img_h: int, class_id: int
) -> str:
    """Convert pixel polygon points to one YOLO-seg line (reference: web_file)."""
    if img_w <= 0 or img_h <= 0 or len(points) < 3:
        return ""
    tokens = [str(class_id)]
    for x, y in points:
        nx = min(max(x / img_w, 0.0), 1.0)
        ny = min(max(y / img_h, 0.0), 1.0)
        tokens.append(f"{nx:.6f}")
        tokens.append(f"{ny:.6f}")
    return " ".join(tokens)


def remap_label_file(path: Path, name_to_id: dict[str, int] | None = None) -> list[str]:
    """
    Remap class IDs in a label file using CVAT export name order file — not used here.
    For files that already have numeric IDs, validate only.
    """
    _ = name_to_id
    return validate_label_file(path).errors
