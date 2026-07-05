# Deferred Modules

These packages are **out of scope** for the YOLO11 7-class segmentation training pipeline.

They are preserved for possible future work but are **not imported** by the active training or annotation path.

| Package | Former path |
|---------|-------------|
| `graph_builder` | `src/graph_builder` |
| `topology_validator` | `src/topology_validator` |
| `bim_schema` | `src/bim_schema` |
| `ifc_adapter` | `src/ifc_adapter` |
| `pipeline` | `src/pipeline` |

Do not add imports from `_deferred` in `scripts/` or active `src/` modules.
