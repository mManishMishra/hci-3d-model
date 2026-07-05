"""
Topology validation for building graphs.

Enforces architectural constraints before BIM JSON export and IFC compilation.
Invalid graphs are rejected or flagged for human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from graph_builder.building_graph import BuildingGraph


class ValidationSeverity(str, Enum):
    """Severity level for a validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCode(str, Enum):
    """Machine-readable validation rule identifiers."""

    WALL_MIN_LENGTH = "WALL_MIN_LENGTH"
    WALL_SNAP_RESIDUAL = "WALL_SNAP_RESIDUAL"
    OPENING_ORPHAN = "OPENING_ORPHAN"
    OPENING_WIDTH = "OPENING_WIDTH"
    ROOM_NOT_CLOSED = "ROOM_NOT_CLOSED"
    ROOM_NOT_SIMPLE = "ROOM_NOT_SIMPLE"
    ROOM_MIN_AREA = "ROOM_MIN_AREA"
    CONFIDENCE_GATE = "CONFIDENCE_GATE"
    EXTERIOR_LOOP = "EXTERIOR_LOOP"
    SCALE_MISSING = "SCALE_MISSING"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding."""

    code: ValidationCode
    severity: ValidationSeverity
    message: str
    entity_id: str | None = None
    suggested_repair: str | None = None


@dataclass(frozen=True)
class ValidationConfig:
    """Thresholds and toggles for validation rules."""

    min_wall_length_m: float = 0.10
    max_snap_residual_m: float = 0.05
    min_opening_width_m: float = 0.60
    max_opening_width_m: float = 3.00
    min_room_area_m2: float = 2.0
    min_mean_confidence: float = 0.30
    fail_on_warnings: bool = False
    enabled_rules: frozenset[ValidationCode] = field(
        default_factory=lambda: frozenset(ValidationCode)
    )


@dataclass(frozen=True)
class ValidationReport:
    """Aggregated validation result for a building graph."""

    image_id: str
    passed: bool
    errors: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    warnings: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.errors) + len(self.warnings)


@runtime_checkable
class ValidationRule(Protocol):
    """Protocol for individual validation rules."""

    code: ValidationCode
    severity: ValidationSeverity

    def check(self, graph: BuildingGraph) -> list[ValidationIssue]:
        """Run this rule against a graph and return any issues."""
        ...


class TopologyValidator:
    """
    Validate building graphs against architectural topology rules.

    Rules include wall connectivity, opening-on-wall constraints, closed room
    polygons, minimum areas, and confidence gating.

    Example:
        >>> validator = TopologyValidator(ValidationConfig())
        >>> report = validator.validate(building_graph)
        >>> if not report.passed:
        ...     raise ValueError(report.errors)
    """

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self._config = config or ValidationConfig()
        self._rules: list[ValidationRule] = []  # TODO: Register default rules

    @property
    def config(self) -> ValidationConfig:
        return self._config

    def validate(self, graph: BuildingGraph) -> ValidationReport:
        """
        Run all enabled validation rules against a building graph.

        Args:
            graph: BuildingGraph to validate.

        Returns:
            ValidationReport with pass/fail, issues, and summary metrics.
        """
        # TODO: Register and iterate ValidationRule implementations
        # TODO: Collect errors and warnings
        # TODO: Compute metrics (wall_count, snap_residual_max, mean_confidence)
        # TODO: Determine passed based on errors and fail_on_warnings
        # TODO: Return ValidationReport
        raise NotImplementedError("TopologyValidator.validate is not yet implemented")

    def register_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule to the validator."""
        # TODO: Append to self._rules
        raise NotImplementedError("TopologyValidator.register_rule is not yet implemented")

    def auto_repair(self, graph: BuildingGraph, report: ValidationReport) -> BuildingGraph:
        """
        Apply safe automatic repairs for warning-level issues.

        Error-level issues are never auto-repaired; they require re-inference
        or human correction.
        """
        # TODO: Snap corners, drop lowest-confidence orphans, merge short segments
        raise NotImplementedError("TopologyValidator.auto_repair is not yet implemented")

    def export_report(self, report: ValidationReport, output_path: str) -> None:
        """Serialize validation report to JSON."""
        # TODO: JSON export
        raise NotImplementedError("TopologyValidator.export_report is not yet implemented")
