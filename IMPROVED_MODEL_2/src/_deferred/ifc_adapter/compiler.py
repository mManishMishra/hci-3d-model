"""
IFC compiler adapter.

Wraps IfcOpenShell and the read-only V3 reference compiler
(``latest_interior_v1/automated_bim_v4_connected.py``) without modifying
legacy project files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bim_schema.building_analysis import BuildingAnalysis


@dataclass(frozen=True)
class IFCAdapterConfig:
    """Configuration for IFC compilation."""

    v3_compiler_root: Path = Path(
        r"D:\HCI_interor\latest_interior_v1\latest_interior_v1"
    )
    schema: str = "IFC4"
    storey_name: str = "Ground Floor"
    compile_spaces: bool = False  # TODO: Enable when RoomData → IfcSpace is implemented
    debug: bool = False


@dataclass(frozen=True)
class IFCCompileResult:
    """Result of an IFC compilation run."""

    output_path: Path
    element_count: int
    wall_count: int
    opening_count: int
    interior_count: int
    room_count: int
    warnings: tuple[str, ...]


class IFCCompilerAdapter:
    """
    Compile BuildingAnalysis JSON to IFC4 via IfcOpenShell.

    Phase 1 delegates to the V3 ``build_detailed_ifc()`` reference implementation.
    Phase 2 adds ``IfcSpace`` compilation from ``RoomData``.

    Example:
        >>> adapter = IFCCompilerAdapter(IFCAdapterConfig())
        >>> result = adapter.compile(analysis, Path("output/model.ifc"))
    """

    def __init__(self, config: IFCAdapterConfig | None = None) -> None:
        self._config = config or IFCAdapterConfig()
        self._compiler_module: Any | None = None

    @property
    def config(self) -> IFCAdapterConfig:
        return self._config

    def compile(self, analysis: BuildingAnalysis, output_path: Path) -> IFCCompileResult:
        """
        Generate an IFC4 file from BuildingAnalysis.

        Args:
            analysis: Validated BIM JSON model.
            output_path: Destination ``.ifc`` file path.

        Returns:
            IFCCompileResult with counts and warnings.

        Raises:
            FileNotFoundError: If V3 compiler root is not found.
            RuntimeError: If IfcOpenShell compilation fails.
        """
        # TODO: Load V3 compiler module via importlib (read-only sys.path insert)
        # TODO: Convert BuildingAnalysis to V3-compatible model if needed
        # TODO: Call build_detailed_ifc(analysis, str(output_path))
        # TODO: Optionally compile IfcSpace from analysis.rooms
        # TODO: Count elements and return IFCCompileResult
        raise NotImplementedError("IFCCompilerAdapter.compile is not yet implemented")

    def load_v3_compiler(self) -> Any:
        """Dynamically import the V3 reference compiler module."""
        # TODO: importlib.util.spec_from_file_location from v3_compiler_root
        raise NotImplementedError("IFCCompilerAdapter.load_v3_compiler is not yet implemented")

    def validate_output(self, ifc_path: Path) -> list[str]:
        """Basic post-compile validation (schema, entity counts)."""
        # TODO: ifcopenshell.open + sanity checks
        raise NotImplementedError("IFCCompilerAdapter.validate_output is not yet implemented")
