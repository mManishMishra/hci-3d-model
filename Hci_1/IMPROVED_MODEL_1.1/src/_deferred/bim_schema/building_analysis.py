"""
BIM JSON schema — BuildingAnalysis contract.

Defines the canonical interchange format between the vision/graph pipeline
and the IFC compiler. Compatible with V3 ``latest_interior_v1`` schema with
extensions for rooms, scale provenance, and pipeline metadata.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ElementProperty(BaseModel):
    """IFC property override row."""

    name: str = Field(description="IFC property name, e.g. BedSize, SeatingCapacity")
    value: str = Field(description="Property value as text")
    pset: str | None = Field(default=None, description="Optional property set name")


class WallData(BaseModel):
    """Wall segment as centerline in metric coordinates."""

    wall_id: str
    start_pt: list[float] = Field(description="Centerline start [x, y] in metres")
    end_pt: list[float] = Field(description="Centerline end [x, y] in metres")
    thickness: float = Field(default=0.23, gt=0)
    height: float = Field(default=3.0, gt=0)
    unit: str = Field(default="m")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class OpeningComponent(BaseModel):
    """Door, window, or arch opening."""

    id: str
    type: str = Field(description="door, window, or arch")
    location_pt: list[float] = Field(description="Center [x, y] in metres")
    width: float = Field(default=0.90, gt=0)
    height: float = Field(default=2.10, gt=0)
    parent_wall_id: str
    operation_type: str | None = None
    material: str | None = None
    color: list[float] | None = Field(default=None, description="RGB 0–1")
    properties: list[ElementProperty] = Field(default_factory=list)
    unit: str = Field(default="m")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class InteriorComponent(BaseModel):
    """Furniture, sanitary fixture, or appliance."""

    id: str
    category: str = Field(description="furnishing, sanitary, or appliance")
    type: str | None = Field(default=None, description="e.g. BED, SOFA, WC")
    location_pt: list[float]
    dimensions: list[float] = Field(default_factory=lambda: [0.8, 0.8, 0.5], description="[w, d, h]")
    material: str | None = None
    color: list[float] | None = None
    properties: list[ElementProperty] = Field(default_factory=list)
    unit: str = Field(default="m")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class RoomData(BaseModel):
    """Room / space boundary — enables future IfcSpace compilation."""

    room_id: str
    label: str | None = None
    polygon: list[list[float]] = Field(default_factory=list, description="Boundary [x,y] in metres")
    unit: str = Field(default="m")
    area_m2: float | None = Field(default=None, gt=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ScaleMetadata(BaseModel):
    """Scale calibration attached to the building model."""

    metres_per_pixel: float = Field(gt=0)
    source: str = Field(default="unknown")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reference: str | None = None


class ProvenanceMetadata(BaseModel):
    """Pipeline provenance for audit and reproducibility."""

    pipeline_version: str = "0.1.0"
    detection_model: str | None = None
    graph_builder_version: str | None = None
    validation_passed: bool = False
    element_confidences: dict[str, float] = Field(default_factory=dict)


class BuildingAnalysis(BaseModel):
    """
    Root BIM JSON schema — downstream contract for IFC generation.

    Extends V3 ``BuildingAnalysis`` with ``rooms``, ``scale``, ``schema_version``,
    and ``provenance`` fields.
    """

    schema_version: str = Field(default="1.1")
    building_name: str = Field(default="Floor Plan")
    scale: ScaleMetadata | None = None
    walls: list[WallData]
    openings: list[OpeningComponent] = Field(default_factory=list)
    interiors: list[InteriorComponent] = Field(default_factory=list)
    rooms: list[RoomData] = Field(default_factory=list)
    provenance: ProvenanceMetadata | None = None

    @field_validator("walls")
    @classmethod
    def require_at_least_one_wall(cls, value: list[WallData]) -> list[WallData]:
        if not value:
            raise ValueError("BuildingAnalysis requires at least one wall")
        return value

    def to_json_dict(self) -> dict[str, Any]:
        """Export as JSON-serializable dict."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> BuildingAnalysis:
        """Load from JSON dict (e.g. cached extraction file)."""
        return cls.model_validate(data)


class BuildingAnalysisAdapter:
    """
    Convert a validated BuildingGraph into BuildingAnalysis JSON.

    Example:
        >>> adapter = BuildingAnalysisAdapter()
        >>> analysis = adapter.from_graph(building_graph)
    """

    def from_graph(self, graph: Any) -> BuildingAnalysis:  # TODO: BuildingGraph type
        """
        Map graph nodes/edges/openings/rooms to BuildingAnalysis fields.

        Args:
            graph: Validated BuildingGraph instance.

        Returns:
            BuildingAnalysis ready for IFC compilation.
        """
        # TODO: Map GraphEdge → WallData with sequential wall_ids
        # TODO: Map GraphOpening → OpeningComponent with parent_wall_id
        # TODO: Map GraphRoom → RoomData
        # TODO: Attach scale and provenance metadata
        raise NotImplementedError("BuildingAnalysisAdapter.from_graph is not yet implemented")

    def to_graph(self, analysis: BuildingAnalysis) -> Any:
        """Reconstruct a BuildingGraph from BuildingAnalysis (inverse mapping)."""
        # TODO: Reverse mapping for editing workflows
        raise NotImplementedError("BuildingAnalysisAdapter.to_graph is not yet implemented")
