"""
Building graph construction.

Converts pixel-space detections (walls, doors, windows, rooms) into a
metric spatial graph suitable for topology validation and BIM JSON export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import networkx as nx
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the building graph."""

    CORNER = "corner"
    OPENING_CENTER = "opening_center"
    ROOM_CENTROID = "room_centroid"


class EdgeType(str, Enum):
    """Types of edges in the building graph."""

    WALL = "wall"


class OpeningType(str, Enum):
    """Opening classification."""

    DOOR = "door"
    WINDOW = "window"
    ARCH = "arch"


class ScaleSource(str, Enum):
    """Provenance of scale calibration."""

    OCR = "ocr"
    DOOR_PRIOR = "door_prior"
    SVG_METADATA = "svg_metadata"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ScaleMetadata(BaseModel):
    """Pixel-to-metre scale calibration result."""

    metres_per_pixel: float = Field(gt=0, description="Conversion factor from pixels to metres")
    source: ScaleSource = ScaleSource.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reference: str | None = Field(default=None, description="Human-readable scale reference")


class GraphNode(BaseModel):
    """A node in the building graph."""

    id: str
    node_type: NodeType
    position_px: tuple[float, float]
    position_m: tuple[float, float] | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphEdge(BaseModel):
    """A wall edge connecting two corner nodes."""

    id: str
    edge_type: EdgeType = EdgeType.WALL
    start_node_id: str
    end_node_id: str
    thickness_m: float = 0.23
    height_m: float = 3.0
    is_exterior: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_detection_ids: list[str] = Field(default_factory=list)


class GraphOpening(BaseModel):
    """An opening attached to a wall edge."""

    id: str
    opening_type: OpeningType
    host_edge_id: str
    position_on_edge: float = Field(ge=0.0, le=1.0, description="Parametric position 0–1 along edge")
    width_m: float = 0.90
    height_m: float = 2.10
    center_px: tuple[float, float] | None = None
    center_m: tuple[float, float] | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphRoom(BaseModel):
    """A room face derived from room segmentation or graph cycles."""

    id: str
    label: str | None = None
    polygon_px: list[tuple[float, float]] = Field(default_factory=list)
    polygon_m: list[tuple[float, float]] = Field(default_factory=list)
    area_m2: float | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class BuildingGraph(BaseModel):
    """
    Metric building graph — interchange format between detection and BIM schema.

    Wraps a NetworkX graph for algorithms while maintaining serializable
    Pydantic models for persistence.
    """

    schema_version: str = "1.0"
    image_id: str
    scale: ScaleMetadata | None = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    openings: list[GraphOpening] = Field(default_factory=list)
    rooms: list[GraphRoom] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_networkx(self) -> nx.Graph:
        """Build a NetworkX graph for topology algorithms."""
        # TODO: Add nodes and edges with attributes
        raise NotImplementedError("BuildingGraph.to_networkx is not yet implemented")

    @classmethod
    def from_networkx(
        cls,
        graph: nx.Graph,
        image_id: str,
        scale: ScaleMetadata | None = None,
    ) -> BuildingGraph:
        """Reconstruct BuildingGraph from a NetworkX graph."""
        # TODO: Extract nodes, edges, openings from nx attributes
        raise NotImplementedError("BuildingGraph.from_networkx is not yet implemented")


@dataclass(frozen=True)
class GraphBuildConfig:
    """Configuration for graph construction."""

    snap_tolerance_px: float = 5.0
    collinear_merge_angle_deg: float = 3.0
    opening_max_distance_px: float = 20.0
    default_wall_thickness_m: float = 0.23
    default_wall_height_m: float = 3.0
    default_door_width_m: float = 0.90
    exterior_loop_required: bool = False


class BuildingGraphBuilder:
    """
    Build a metric BuildingGraph from detection outputs.

    Planned pipeline:
        1. Extract wall centerlines from wall masks
        2. Snap corners and merge collinear segments
        3. Calibrate pixel → metre scale
        4. Assign openings to nearest wall edges
        5. Extract room polygons

    Example:
        >>> builder = BuildingGraphBuilder(GraphBuildConfig())
        >>> graph = builder.build(detections, image_id="abc123")
    """

    def __init__(self, config: GraphBuildConfig | None = None) -> None:
        self._config = config or GraphBuildConfig()

    @property
    def config(self) -> GraphBuildConfig:
        return self._config

    def build(
        self,
        detections: Any,  # TODO: Replace with DetectionResult type from detection layer
        image_id: str,
        scale: ScaleMetadata | None = None,
    ) -> BuildingGraph:
        """
        Construct a BuildingGraph from detection results.

        Args:
            detections: Model output with wall/door/window/room instances.
            image_id: Stable identifier for the source image.
            scale: Optional pre-computed scale; estimated if None.

        Returns:
            Populated BuildingGraph in metric coordinates.
        """
        # TODO: Extract wall segments from detection masks/polylines
        # TODO: Snap corners within snap_tolerance_px
        # TODO: Merge collinear segments
        # TODO: Estimate scale if not provided
        # TODO: Convert all coordinates to metres
        # TODO: Assign openings to host edges
        # TODO: Build room polygons
        # TODO: Return BuildingGraph
        raise NotImplementedError("BuildingGraphBuilder.build is not yet implemented")

    def snap_corners(self, segments: list[Any]) -> list[Any]:
        """Merge endpoints within snap tolerance."""
        # TODO: Cluster endpoints, replace with canonical corner coordinates
        raise NotImplementedError("BuildingGraphBuilder.snap_corners is not yet implemented")

    def merge_collinear(self, segments: list[Any]) -> list[Any]:
        """Merge adjacent collinear wall segments."""
        # TODO: Angle + gap check, merge into single segment
        raise NotImplementedError("BuildingGraphBuilder.merge_collinear is not yet implemented")

    def assign_openings(
        self,
        openings: list[Any],
        edges: list[GraphEdge],
    ) -> list[GraphOpening]:
        """Project opening centroids onto nearest wall edges."""
        # TODO: Point-to-segment distance, parametric position
        raise NotImplementedError("BuildingGraphBuilder.assign_openings is not yet implemented")

    def extract_rooms(self, room_detections: list[Any]) -> list[GraphRoom]:
        """Convert room detection masks to GraphRoom polygons."""
        # TODO: Contour extraction, area calculation, optional OCR label join
        raise NotImplementedError("BuildingGraphBuilder.extract_rooms is not yet implemented")
