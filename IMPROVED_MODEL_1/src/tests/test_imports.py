"""Smoke tests — verify package imports and schema instantiation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bim_schema.building_analysis import BuildingAnalysis, WallData
from dataset_tools.dataset_audit import DatasetAuditor, DatasetAuditConfig
from dataset_tools.dataset_cleaner import DatasetCleaner, DatasetCleanConfig
from graph_builder.building_graph import BuildingGraphBuilder
from ifc_adapter.compiler import IFCCompilerAdapter
from pipeline.run_pipeline import PipelineRunner
from preprocessing.image_preprocessor import ImagePreprocessor
from topology_validator.validator import TopologyValidator


def test_package_imports() -> None:
    """All public entry points are importable."""
    assert DatasetAuditor is not None
    assert DatasetCleaner is not None
    assert ImagePreprocessor is not None
    assert BuildingGraphBuilder is not None
    assert TopologyValidator is not None
    assert IFCCompilerAdapter is not None
    assert PipelineRunner is not None


def test_building_analysis_requires_walls() -> None:
    """BuildingAnalysis schema enforces at least one wall."""
    with pytest.raises(ValidationError):
        BuildingAnalysis(walls=[])


def test_building_analysis_minimal_valid() -> None:
    """Minimal valid BuildingAnalysis can be constructed."""
    analysis = BuildingAnalysis(
        walls=[
            WallData(
                wall_id="wall_001",
                start_pt=[0.0, 0.0],
                end_pt=[5.0, 0.0],
            )
        ]
    )
    assert analysis.schema_version == "1.1"
    assert len(analysis.walls) == 1


def test_skeleton_methods_raise_not_implemented() -> None:
    """Unimplemented pipeline methods raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        PipelineRunner().run(__import__("pathlib").Path("dummy.jpg"))
