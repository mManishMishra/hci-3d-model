"""
End-to-end pipeline orchestration.

Chains preprocessing → detection → graph → validation → BIM JSON → IFC
with inspectable artifacts at each stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bim_schema.building_analysis import BuildingAnalysis
    from graph_builder.building_graph import BuildingGraph
    from preprocessing.image_preprocessor import PreprocessedImage
    from topology_validator.validator import ValidationReport


class PipelineStage(str, Enum):
    """Ordered pipeline stages."""

    PREPROCESS = "preprocess"
    DETECT = "detect"
    GRAPH = "graph"
    VALIDATE = "validate"
    BIM = "bim"
    IFC = "ifc"


@dataclass(frozen=True)
class PipelineConfig:
    """Master configuration for a pipeline run."""

    artifacts_dir: Path = Path("experiments/runs")
    fail_on_validation_error: bool = True
    resume_from: PipelineStage | None = None
    enabled_stages: frozenset[PipelineStage] = field(
        default_factory=lambda: frozenset(PipelineStage)
    )
    v3_compiler_root: Path = Path(
        r"D:\HCI_interor\latest_interior_v1\latest_interior_v1"
    )


@dataclass
class PipelineResult:
    """Aggregated outputs from a pipeline run."""

    run_id: str
    source_path: Path
    preprocessed: PreprocessedImage | None = None
    detections: Any | None = None  # TODO: DetectionResult
    graph: BuildingGraph | None = None
    validation: ValidationReport | None = None
    building_analysis: BuildingAnalysis | None = None
    ifc_path: Path | None = None
    artifacts: dict[str, Path] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return not self.errors and self.ifc_path is not None


class PipelineRunner:
    """
    Orchestrate the full floor plan → IFC pipeline.

    Each stage writes artifacts under ``{artifacts_dir}/{run_id}/`` for
    debugging and resume capability.

    Example:
        >>> config = PipelineConfig(artifacts_dir=Path("experiments/runs"))
        >>> runner = PipelineRunner(config)
        >>> result = runner.run(Path("data/plan.jpg"))
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self._config = config or PipelineConfig()

    @property
    def config(self) -> PipelineConfig:
        return self._config

    def run(self, source_path: Path) -> PipelineResult:
        """
        Execute the pipeline on a single floor plan image.

        Args:
            source_path: Path to input image (JPG, PNG, JFIF, GIF, SVG).

        Returns:
            PipelineResult with stage outputs and artifact paths.
        """
        # TODO: Generate run_id from timestamp + source stem
        # TODO: Create artifacts directory
        # TODO: Stage PREPROCESS — ImagePreprocessor.process()
        # TODO: Stage DETECT — YOLODetector.predict() (when detection layer exists)
        # TODO: Stage GRAPH — BuildingGraphBuilder.build()
        # TODO: Stage VALIDATE — TopologyValidator.validate()
        # TODO: Stage BIM — BuildingAnalysisAdapter.from_graph()
        # TODO: Stage IFC — IFCCompilerAdapter.compile()
        # TODO: Persist artifacts JSON at each stage
        # TODO: Return PipelineResult
        raise NotImplementedError("PipelineRunner.run is not yet implemented")

    def run_from_stage(self, source_path: Path, stage: PipelineStage) -> PipelineResult:
        """Resume pipeline execution from a specific stage using cached artifacts."""
        # TODO: Load artifacts from prior run, skip earlier stages
        raise NotImplementedError("PipelineRunner.run_from_stage is not yet implemented")

    def run_batch(self, source_dir: Path) -> list[PipelineResult]:
        """Process all images in a directory."""
        # TODO: Glob images, run sequentially or via job queue
        raise NotImplementedError("PipelineRunner.run_batch is not yet implemented")

    def _artifact_path(self, run_id: str, name: str) -> Path:
        """Resolve path for a named artifact within a run directory."""
        return self._config.artifacts_dir / run_id / name

    def _save_artifact(self, run_id: str, name: str, data: Any) -> Path:
        """Serialize stage output to the artifacts directory."""
        # TODO: JSON for models, PNG for images, IFC for compile output
        raise NotImplementedError("PipelineRunner._save_artifact is not yet implemented")
