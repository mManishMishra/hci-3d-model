#!/usr/bin/env python3
"""
HCI_2.1 IFC geometry pipeline (Day 3/4 library).
Builds walls + openings + doors/windows IFC4 from YOLO-seg labels.
Does NOT touch best_gdrive.pt or Hci_1.
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# Optional IfcOpenShell — import at call time for clearer errors
WALL_H = 3.0
DOOR_H = 2.1
WIN_H = 1.2
WIN_SILL = 0.9
THICK_FALLBACK = 0.23
THICK_MIN, THICK_MAX = 0.10, 0.40
SNAP_PX = 20.0
OPEN_MAX_DIST_M = 0.55

# HCI / CubiCasa aligned IDs for architectural IFC
CLASS_WALL = 3
CLASS_DOOR = 2
CLASS_WINDOW = 1


def yolo_polys(lbl: Path, class_id: int, W: int, H: int) -> list[dict]:
    out = []
    text = lbl.read_text(encoding="utf-8")
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) < 7:
            continue
        if int(float(parts[0])) != class_id:
            continue
        coords = list(map(float, parts[1:]))
        pts = []
        for k in range(0, len(coords) - 1, 2):
            pts.append([coords[k] * W, coords[k + 1] * H])
        if len(pts) < 3:
            continue
        if pts[0] != pts[-1]:
            pts.append(pts[0][:])
        arr = np.array(pts, dtype=np.float32)
        area = float(abs(cv2.contourArea(arr)))
        out.append({"id": f"c{class_id}_{len(out)}", "class": class_id, "points_px": pts, "area_px": area})
    return out


def min_area_centerline(pts_px: list[list[float]]) -> tuple[list[list[float]], float, float]:
    cnt = np.array(pts_px, dtype=np.float32).reshape(-1, 1, 2)
    rect = cv2.minAreaRect(cnt)
    (cx, cy), (w, h), angle = rect
    if w < h:
        w, h = h, w
        angle += 90.0
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    half = w / 2.0
    p1 = [cx - dx * half, cy - dy * half]
    p2 = [cx + dx * half, cy + dy * half]
    thick = max(float(h), 2.0)
    return [p1, p2], thick, float(w)


def dist_point_to_segment(px, py, ax, ay, bx, by) -> tuple[float, float, float, float]:
    abx, aby = bx - ax, by - ay
    len2 = abx * abx + aby * aby
    if len2 < 1e-12:
        return math.hypot(px - ax, py - ay), 0.0, ax, ay
    t = ((px - ax) * abx + (py - ay) * aby) / len2
    t_clamped = max(0.0, min(1.0, t))
    qx, qy = ax + t_clamped * abx, ay + t_clamped * aby
    return math.hypot(px - qx, py - qy), t_clamped, qx, qy


def build_wall_graph(walls: list[dict], W: int, H: int, mpp: float, warnings: list[str]) -> dict:
    raw_segs = []
    for w in walls:
        poly, thick_px, length_px = min_area_centerline(w["points_px"])
        raw_segs.append(
            {
                "id": f"w{len(raw_segs)}",
                "source_polygon_id": w["id"],
                "polyline_px": poly,
                "thickness_px": thick_px,
                "length_px": length_px,
            }
        )

    endpoints: list[tuple[float, float, int, str]] = []
    for i, s in enumerate(raw_segs):
        endpoints.append((s["polyline_px"][0][0], s["polyline_px"][0][1], i, "a"))
        endpoints.append((s["polyline_px"][-1][0], s["polyline_px"][-1][1], i, "b"))

    n = len(endpoints)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if math.hypot(endpoints[i][0] - endpoints[j][0], endpoints[i][1] - endpoints[j][1]) <= SNAP_PX:
                union(i, j)

    # T-junction soft snap
    for ei, (ex, ey, si, which) in enumerate(list(endpoints)):
        best_d, best_sj, best_t = 1e18, -1, 0.0
        for sj, s in enumerate(raw_segs):
            if sj == si:
                continue
            ax, ay = s["polyline_px"][0]
            bx, by = s["polyline_px"][-1]
            d, t, qx, qy = dist_point_to_segment(ex, ey, ax, ay, bx, by)
            if 0.05 < t < 0.95 and d < SNAP_PX and d < best_d:
                best_d, best_sj, best_t = d, sj, t
        if best_sj >= 0:
            ax, ay = raw_segs[best_sj]["polyline_px"][0]
            bx, by = raw_segs[best_sj]["polyline_px"][-1]
            qx = ax + best_t * (bx - ax)
            qy = ay + best_t * (by - ay)
            endpoints[ei] = (qx, qy, si, which)

    parent = list(range(n))
    for i in range(n):
        for j in range(i + 1, n):
            if math.hypot(endpoints[i][0] - endpoints[j][0], endpoints[i][1] - endpoints[j][1]) <= SNAP_PX:
                union(i, j)

    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    nodes = []
    ep_to_node: dict[int, str] = {}
    for ci, members in enumerate(clusters.values()):
        xs = [endpoints[i][0] for i in members]
        ys = [endpoints[i][1] for i in members]
        nid = f"n{ci}"
        nodes.append({"id": nid, "x_px": sum(xs) / len(xs), "y_px": sum(ys) / len(ys)})
        for i in members:
            ep_to_node[i] = nid

    for i, s in enumerate(raw_segs):
        ia = next(k for k, e in enumerate(endpoints) if e[2] == i and e[3] == "a")
        ib = next(k for k, e in enumerate(endpoints) if e[2] == i and e[3] == "b")
        na, nb = ep_to_node[ia], ep_to_node[ib]
        na_n = next(n for n in nodes if n["id"] == na)
        nb_n = next(n for n in nodes if n["id"] == nb)
        s["polyline_px"] = [[na_n["x_px"], na_n["y_px"]], [nb_n["x_px"], nb_n["y_px"]]]
        s["length_px"] = math.hypot(nb_n["x_px"] - na_n["x_px"], nb_n["y_px"] - na_n["y_px"])
        s["start_node_id"] = na
        s["end_node_id"] = nb

    def py_to_m(y):
        return (H - y) * mpp

    segments_m = []
    for s in raw_segs:
        raw_tm = s["thickness_px"] * mpp
        thick_m = float(np.clip(raw_tm, THICK_MIN, THICK_MAX))
        if raw_tm > THICK_MAX * 1.5 or raw_tm < THICK_MIN * 0.5:
            thick_m = THICK_FALLBACK
            warnings.append(f"{s['id']} thickness reset to {THICK_FALLBACK}m (raw={raw_tm:.3f}m)")
        poly_m = [[p[0] * mpp, py_to_m(p[1])] for p in s["polyline_px"]]
        segments_m.append(
            {
                **s,
                "polyline_m": poly_m,
                "thickness_m": thick_m,
                "length_m": s["length_px"] * mpp,
            }
        )

    return {
        "W": W,
        "H": H,
        "meters_per_pixel": mpp,
        "nodes": nodes,
        "segments": segments_m,
        "gt_wall_count": len(walls),
    }


def opening_metrics(pts_px: list[list[float]]) -> dict:
    arr = np.array(pts_px, dtype=np.float32)
    cnt = arr.reshape(-1, 1, 2)
    M = cv2.moments(cnt)
    if M["m00"] > 1e-6:
        cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
    else:
        cx, cy = float(np.mean(arr[:, 0])), float(np.mean(arr[:, 1]))
    rect = cv2.minAreaRect(cnt)
    (rcx, rcy), (w, h), angle = rect
    width_px = float(max(w, h))
    depth_px = float(min(w, h))
    if w < h:
        angle += 90.0
    return {
        "centroid_px": [float(cx), float(cy)],
        "width_px": width_px,
        "depth_px": depth_px,
        "orientation_deg": float(angle),
    }


def associate_openings(graph_m: dict, doors: list[dict], wins: list[dict], H: int, mpp: float, warnings: list[str]) -> dict:
    def px_to_m(x, y):
        return x * mpp, (H - y) * mpp

    openings = []
    for o in doors:
        o = dict(o)
        o.update(opening_metrics(o["points_px"]))
        o["type"] = "door"
        openings.append(o)
    for o in wins:
        o = dict(o)
        o.update(opening_metrics(o["points_px"]))
        o["type"] = "window"
        openings.append(o)

    mappings = []
    unmapped = []
    for o in openings:
        cx, cy = o["centroid_px"]
        cx_m, cy_m = px_to_m(cx, cy)
        best = None
        for s in graph_m["segments"]:
            ax, ay = s["polyline_m"][0]
            bx, by = s["polyline_m"][-1]
            d, t, qx, qy = dist_point_to_segment(cx_m, cy_m, ax, ay, bx, by)
            max_d = max(OPEN_MAX_DIST_M, s["thickness_m"] * 1.5 + 0.15)
            if d <= max_d and (best is None or d < best["distance_to_wall"]):
                ang = math.degrees(math.atan2(by - ay, bx - ax))
                best = {
                    "opening_id": o["id"],
                    "opening_type": o["type"],
                    "host_wall_id": s["id"],
                    "distance_to_wall": d,
                    "offset_along_wall": t * s["length_m"],
                    "t": t,
                    "orientation_deg": ang,
                    "width_m": o["width_px"] * mpp,
                    "wall_length_m": s["length_m"],
                    "wall_thickness_m": s["thickness_m"],
                }
        if best is None:
            unmapped.append(o["id"])
            warnings.append(f"unmapped opening {o['id']} ({o['type']})")
        else:
            mappings.append(best)

    return {
        "total_openings": len(openings),
        "successfully_mapped": len(mappings),
        "unmapped": unmapped,
        "unmapped_count": len(unmapped),
        "mapping_success_rate": len(mappings) / len(openings) if openings else 1.0,
        "mappings": mappings,
    }


def write_ifc4(graph_m: dict, opening_map: dict, out_ifc: Path, basename: str) -> dict:
    import ifcopenshell
    import ifcopenshell.guid

    model = ifcopenshell.file(schema="IFC4")
    tnow = int(time.time())
    person = model.create_entity("IfcPerson", Identification="HCI_2.1", FamilyName="HCI")
    org = model.create_entity("IfcOrganization", Name="HCI Interior 2.1")
    p_and_o = model.create_entity("IfcPersonAndOrganization", ThePerson=person, TheOrganization=org)
    app = model.create_entity(
        "IfcApplication",
        ApplicationDeveloper=org,
        Version="2.1",
        ApplicationFullName="HCI_2.1 IFC Export",
        ApplicationIdentifier="hci_2_1_ifc",
    )
    owner = model.create_entity(
        "IfcOwnerHistory",
        OwningUser=p_and_o,
        OwningApplication=app,
        ChangeAction="ADDED",
        CreationDate=tnow,
    )
    unit_l = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
    units = model.create_entity("IfcUnitAssignment", Units=[unit_l])
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    world_pl = model.create_entity("IfcAxis2Placement3D", Location=origin)
    context = model.create_entity(
        "IfcGeometricRepresentationContext",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-05,
        WorldCoordinateSystem=world_pl,
    )
    body_context = model.create_entity(
        "IfcGeometricRepresentationSubContext",
        ContextIdentifier="Body",
        ContextType="Model",
        ParentContext=context,
        TargetView="MODEL_VIEW",
    )
    project = model.create_entity(
        "IfcProject",
        GlobalId=ifcopenshell.guid.new(),
        Name=f"HCI {basename}",
        OwnerHistory=owner,
        RepresentationContexts=[context],
        UnitsInContext=units,
    )
    site = model.create_entity(
        "IfcSite",
        GlobalId=ifcopenshell.guid.new(),
        Name="Site",
        ObjectPlacement=model.create_entity("IfcLocalPlacement", RelativePlacement=world_pl),
    )
    building = model.create_entity(
        "IfcBuilding",
        GlobalId=ifcopenshell.guid.new(),
        Name="Building",
        ObjectPlacement=model.create_entity(
            "IfcLocalPlacement", PlacementRelTo=site.ObjectPlacement, RelativePlacement=world_pl
        ),
    )
    storey_pl = model.create_entity(
        "IfcLocalPlacement", PlacementRelTo=building.ObjectPlacement, RelativePlacement=world_pl
    )
    storey = model.create_entity(
        "IfcBuildingStorey",
        GlobalId=ifcopenshell.guid.new(),
        Name="Ground Floor",
        ObjectPlacement=storey_pl,
        Elevation=0.0,
    )
    model.create_entity(
        "IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=project, RelatedObjects=[site]
    )
    model.create_entity(
        "IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=site, RelatedObjects=[building]
    )
    model.create_entity(
        "IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=building, RelatedObjects=[storey]
    )

    def make_extruded_box(length, width, height, z0=0.0):
        half = width / 2.0
        pts = [
            model.create_entity("IfcCartesianPoint", Coordinates=c)
            for c in [(0.0, -half), (length, -half), (length, half), (0.0, half), (0.0, -half)]
        ]
        profile = model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            OuterCurve=model.create_entity("IfcPolyline", Points=pts),
        )
        if abs(z0) > 1e-9:
            z_origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, float(z0)))
            pos = model.create_entity("IfcAxis2Placement3D", Location=z_origin)
        else:
            pos = world_pl
        return model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=pos,
            ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
            Depth=float(height),
        )

    def assign_body(product, solid):
        rep = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[solid],
        )
        product.Representation = model.create_entity(
            "IfcProductDefinitionShape", Representations=[rep]
        )

    wall_entities = {}
    wall_placements = {}
    elements = []

    for s in graph_m["segments"]:
        x0, y0 = s["polyline_m"][0]
        x1, y1 = s["polyline_m"][-1]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-4:
            continue
        angle = math.atan2(dy, dx)
        thick = float(np.clip(s["thickness_m"], THICK_MIN, THICK_MAX))
        wall_origin = model.create_entity("IfcCartesianPoint", Coordinates=(float(x0), float(y0), 0.0))
        wall_ax = model.create_entity(
            "IfcAxis2Placement3D",
            Location=wall_origin,
            RefDirection=model.create_entity(
                "IfcDirection", DirectionRatios=(math.cos(angle), math.sin(angle), 0.0)
            ),
        )
        wall_loc = model.create_entity(
            "IfcLocalPlacement", PlacementRelTo=storey_pl, RelativePlacement=wall_ax
        )
        ifc_wall = model.create_entity(
            "IfcWall",
            GlobalId=ifcopenshell.guid.new(),
            Name=s["id"],
            OwnerHistory=owner,
            ObjectPlacement=wall_loc,
        )
        assign_body(ifc_wall, make_extruded_box(length, thick, WALL_H))
        wall_entities[s["id"]] = ifc_wall
        wall_placements[s["id"]] = {"placement": wall_loc, "length": length, "thick": thick}
        elements.append(ifc_wall)

    door_count = win_count = opening_count = 0
    for m in opening_map["mappings"]:
        wid = m["host_wall_id"]
        if wid not in wall_entities:
            continue
        wp = wall_placements[wid]
        wall = wall_entities[wid]
        length = wp["length"]
        thick = wp["thick"]
        width = float(max(0.4, min(m["width_m"], length * 0.9)))
        t = m["t"]
        local_x = t * length - width / 2.0
        local_x = max(0.05, min(local_x, length - width - 0.05))
        if m["opening_type"] == "door":
            oh, z0 = DOOR_H, 0.0
        else:
            oh, z0 = WIN_H, WIN_SILL

        op_origin = model.create_entity("IfcCartesianPoint", Coordinates=(float(local_x), 0.0, 0.0))
        op_ax = model.create_entity("IfcAxis2Placement3D", Location=op_origin)
        op_loc = model.create_entity(
            "IfcLocalPlacement", PlacementRelTo=wp["placement"], RelativePlacement=op_ax
        )
        opening = model.create_entity(
            "IfcOpeningElement",
            GlobalId=ifcopenshell.guid.new(),
            Name=f"opening_{m['opening_id']}",
            OwnerHistory=owner,
            ObjectPlacement=op_loc,
        )
        assign_body(opening, make_extruded_box(width, thick * 1.05, oh, z0=z0))
        model.create_entity(
            "IfcRelVoidsElement",
            GlobalId=ifcopenshell.guid.new(),
            RelatingBuildingElement=wall,
            RelatedOpeningElement=opening,
        )
        opening_count += 1

        fill_loc = model.create_entity(
            "IfcLocalPlacement", PlacementRelTo=wp["placement"], RelativePlacement=op_ax
        )
        if m["opening_type"] == "door":
            door = model.create_entity(
                "IfcDoor",
                GlobalId=ifcopenshell.guid.new(),
                Name=m["opening_id"],
                OwnerHistory=owner,
                ObjectPlacement=fill_loc,
                OverallHeight=DOOR_H,
                OverallWidth=width,
            )
            assign_body(door, make_extruded_box(width * 0.98, min(0.05, thick * 0.4), DOOR_H))
            model.create_entity(
                "IfcRelFillsElement",
                GlobalId=ifcopenshell.guid.new(),
                RelatingOpeningElement=opening,
                RelatedBuildingElement=door,
            )
            elements.append(door)
            door_count += 1
        else:
            win = model.create_entity(
                "IfcWindow",
                GlobalId=ifcopenshell.guid.new(),
                Name=m["opening_id"],
                OwnerHistory=owner,
                ObjectPlacement=fill_loc,
                OverallHeight=WIN_H,
                OverallWidth=width,
            )
            assign_body(win, make_extruded_box(width * 0.98, min(0.05, thick * 0.4), WIN_H, z0=WIN_SILL))
            model.create_entity(
                "IfcRelFillsElement",
                GlobalId=ifcopenshell.guid.new(),
                RelatingOpeningElement=opening,
                RelatedBuildingElement=win,
            )
            elements.append(win)
            win_count += 1

    if elements:
        model.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=ifcopenshell.guid.new(),
            RelatingStructure=storey,
            RelatedElements=elements,
        )

    out_ifc.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(out_ifc))
    return {
        "walls": len(wall_entities),
        "openings": opening_count,
        "doors": door_count,
        "windows": win_count,
    }


def generate_full_ifc(
    image_path: str | Path,
    label_path: str | Path,
    output_ifc: str | Path,
    meters_per_pixel: float,
    work_dir: str | Path | None = None,
) -> dict:
    """
    End-to-end IFC generation from an image + YOLO-seg label file.
    Returns a result dict with counts, mapping stats, warnings, paths.
    """
    warnings: list[str] = []
    image_path = Path(image_path)
    label_path = Path(label_path)
    output_ifc = Path(output_ifc)
    if not image_path.is_file():
        raise FileNotFoundError(f"image not found: {image_path}")
    if not label_path.is_file():
        raise FileNotFoundError(f"label not found: {label_path}")
    if meters_per_pixel <= 0:
        raise ValueError("meters_per_pixel must be > 0")

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"cannot read image: {image_path}")
    H, W = img.shape[:2]
    basename = image_path.stem

    walls = yolo_polys(label_path, CLASS_WALL, W, H)
    doors = yolo_polys(label_path, CLASS_DOOR, W, H)
    wins = yolo_polys(label_path, CLASS_WINDOW, W, H)
    if not walls:
        raise ValueError("No Wall (class 3) polygons found in label file")

    graph_m = build_wall_graph(walls, W, H, float(meters_per_pixel), warnings)
    opening_map = associate_openings(graph_m, doors, wins, H, float(meters_per_pixel), warnings)
    counts = write_ifc4(graph_m, opening_map, output_ifc, basename)

    # Optional debug sidecars
    if work_dir is not None:
        wd = Path(work_dir)
        wd.mkdir(parents=True, exist_ok=True)
        (wd / f"{basename}_wall_graph_m.json").write_text(json.dumps(graph_m, indent=2), encoding="utf-8")
        (wd / f"{basename}_opening_wall_map.json").write_text(
            json.dumps(opening_map, indent=2), encoding="utf-8"
        )

    xs = [p[0] for s in graph_m["segments"] for p in s["polyline_m"]]
    ys = [p[1] for s in graph_m["segments"] for p in s["polyline_m"]]
    bbox = {
        "size_x_m": max(xs) - min(xs) if xs else 0,
        "size_y_m": max(ys) - min(ys) if ys else 0,
        "height_m": WALL_H,
    }

    return {
        "ok": True,
        "basename": basename,
        "ifc_path": str(output_ifc),
        "meters_per_pixel": float(meters_per_pixel),
        "gt_walls": len(walls),
        "gt_doors": len(doors),
        "gt_windows": len(wins),
        "ifc_walls": counts["walls"],
        "ifc_openings": counts["openings"],
        "ifc_doors": counts["doors"],
        "ifc_windows": counts["windows"],
        "mapping_success_rate": opening_map["mapping_success_rate"],
        "mapped_openings": opening_map["successfully_mapped"],
        "unmapped_openings": opening_map["unmapped_count"],
        "bbox_m": bbox,
        "warnings": warnings,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
