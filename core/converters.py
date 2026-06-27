"""
Entity converters: turn DXF entities into Blender data blocks.

Strategy:
    - Linear / curved entities  -> Blender Curve (preserves CAD accuracy,
      stays editable, faster to import than meshing every spline).
    - Filled / planar entities  -> Blender Mesh.
    - INSERT (block ref)        -> handled by operator (collection instances).

All coordinates are scaled by the operator before entities reach here, so
this module is unit-agnostic.
"""

from __future__ import annotations

import math
from typing import Optional

import bpy
from mathutils import Matrix, Vector


# --- Public converter dispatcher --------------------------------------------
def convert_entity(
    entity,
    scale: float,
    *,
    curve_resolution: int = 32,
    import_text: bool = True,
    flatten_z: bool = False,
) -> Optional[bpy.types.Object]:
    """
    Convert a DXF entity to a Blender object. Returns None if unsupported
    or if the entity should be skipped (e.g. TEXT when import_text=False).
    The returned object is NOT yet linked to any collection.
    """
    dxftype = entity.dxftype()

    try:
        if dxftype == "LINE":
            return _line(entity, scale, flatten_z)

        if dxftype in ("LWPOLYLINE", "POLYLINE"):
            return _polyline(entity, scale, flatten_z)

        if dxftype == "CIRCLE":
            return _circle(entity, scale, flatten_z)

        if dxftype == "ARC":
            return _arc(entity, scale, curve_resolution, flatten_z)

        if dxftype == "ELLIPSE":
            return _ellipse(entity, scale, curve_resolution, flatten_z)

        if dxftype == "SPLINE":
            return _spline(entity, scale, curve_resolution, flatten_z)

        if dxftype == "POINT":
            return _point(entity, scale, flatten_z)

        if dxftype in ("3DFACE", "SOLID"):
            return _face(entity, scale, flatten_z)

        if dxftype in ("TEXT", "MTEXT") and import_text:
            return _text(entity, scale, flatten_z)

    except Exception as e:
        # One bad entity should not abort the entire import.
        print(f"[CAD Importer] Skipped {dxftype}: {e}")
        return None

    return None  # Unsupported entity type


# --- Helpers ----------------------------------------------------------------
def _v(point, scale: float, flatten_z: bool) -> Vector:
    """Scale a point and optionally flatten Z to 0."""
    x = point[0] * scale
    y = point[1] * scale
    z = 0.0 if flatten_z else (point[2] * scale if len(point) > 2 else 0.0)
    return Vector((x, y, z))


def _new_curve(name: str) -> bpy.types.Curve:
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    return curve


# --- Per-entity converters --------------------------------------------------
def _line(entity, scale, flatten_z) -> bpy.types.Object:
    curve = _new_curve("DXF_Line")
    spline = curve.splines.new("POLY")
    spline.points.add(1)  # POLY splines start with 1 point
    p1 = _v(entity.dxf.start, scale, flatten_z)
    p2 = _v(entity.dxf.end, scale, flatten_z)
    spline.points[0].co = (*p1, 1.0)
    spline.points[1].co = (*p2, 1.0)
    return bpy.data.objects.new("DXF_Line", curve)


def _polyline(entity, scale, flatten_z) -> bpy.types.Object:
    curve = _new_curve("DXF_Polyline")
    spline = curve.splines.new("POLY")

    # LWPOLYLINE: get_points returns (x, y, start_width, end_width, bulge)
    # POLYLINE (2D/3D): iterate vertices via .points()
    if entity.dxftype() == "LWPOLYLINE":
        pts = [(p[0], p[1], entity.dxf.elevation) for p in entity.get_points()]
    else:
        pts = [tuple(v) for v in entity.points()]

    if not pts:
        return None

    spline.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        v = _v(p, scale, flatten_z)
        spline.points[i].co = (*v, 1.0)

    if getattr(entity, "closed", False) or getattr(entity, "is_closed", False):
        spline.use_cyclic_u = True

    return bpy.data.objects.new("DXF_Polyline", curve)


def _circle(entity, scale, flatten_z) -> bpy.types.Object:
    curve = _new_curve("DXF_Circle")
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(3)  # 4 bezier points = closed circle
    spline.use_cyclic_u = True

    center = _v(entity.dxf.center, scale, flatten_z)
    r = entity.dxf.radius * scale
    # Magic constant for ~circular bezier (4/3 * tan(pi/8))
    handle = r * 0.5522847498

    offsets = [(r, 0), (0, r), (-r, 0), (0, -r)]
    h_offsets = [(0, handle), (-handle, 0), (0, -handle), (handle, 0)]

    for i, (off, ho) in enumerate(zip(offsets, h_offsets)):
        bp = spline.bezier_points[i]
        bp.co = center + Vector((off[0], off[1], 0))
        bp.handle_left = bp.co + Vector((-ho[0], -ho[1], 0))
        bp.handle_right = bp.co + Vector((ho[0], ho[1], 0))
        bp.handle_left_type = "ALIGNED"
        bp.handle_right_type = "ALIGNED"

    return bpy.data.objects.new("DXF_Circle", curve)


def _arc(entity, scale, resolution, flatten_z) -> bpy.types.Object:
    curve = _new_curve("DXF_Arc")
    spline = curve.splines.new("POLY")

    center = _v(entity.dxf.center, scale, flatten_z)
    r = entity.dxf.radius * scale
    start = math.radians(entity.dxf.start_angle)
    end = math.radians(entity.dxf.end_angle)
    if end < start:
        end += 2 * math.pi

    steps = max(2, int(resolution * (end - start) / (2 * math.pi)))
    spline.points.add(steps)  # add N -> N+1 total points
    for i in range(steps + 1):
        t = start + (end - start) * (i / steps)
        p = center + Vector((math.cos(t) * r, math.sin(t) * r, 0))
        spline.points[i].co = (*p, 1.0)

    return bpy.data.objects.new("DXF_Arc", curve)


def _ellipse(entity, scale, resolution, flatten_z) -> bpy.types.Object:
    curve = _new_curve("DXF_Ellipse")
    spline = curve.splines.new("POLY")

    center = _v(entity.dxf.center, scale, flatten_z)
    major = Vector(entity.dxf.major_axis) * scale
    ratio = entity.dxf.ratio
    minor = Vector((-major.y, major.x, 0)) * ratio

    start = entity.dxf.start_param
    end = entity.dxf.end_param
    if end < start:
        end += 2 * math.pi

    steps = max(8, int(resolution * (end - start) / (2 * math.pi)))
    spline.points.add(steps)
    for i in range(steps + 1):
        t = start + (end - start) * (i / steps)
        p = center + major * math.cos(t) + minor * math.sin(t)
        spline.points[i].co = (*p, 1.0)

    if abs(end - start - 2 * math.pi) < 1e-6:
        spline.use_cyclic_u = True

    return bpy.data.objects.new("DXF_Ellipse", curve)


def _spline(entity, scale, resolution, flatten_z) -> bpy.types.Object:
    curve = _new_curve("DXF_Spline")
    spline = curve.splines.new("NURBS")

    # Use control points; flattened or fit_points fall through if unavailable
    try:
        control_pts = list(entity.control_points)
    except AttributeError:
        control_pts = list(getattr(entity, "fit_points", []))

    if not control_pts:
        return None

    spline.points.add(len(control_pts) - 1)
    for i, p in enumerate(control_pts):
        v = _v(p, scale, flatten_z)
        spline.points[i].co = (*v, 1.0)

    spline.order_u = min(getattr(entity.dxf, "degree", 3) + 1, len(control_pts))
    spline.use_endpoint_u = True
    if getattr(entity, "closed", False):
        spline.use_cyclic_u = True

    return bpy.data.objects.new("DXF_Spline", curve)


def _point(entity, scale, flatten_z) -> bpy.types.Object:
    empty = bpy.data.objects.new("DXF_Point", None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.05
    empty.location = _v(entity.dxf.location, scale, flatten_z)
    return empty


def _face(entity, scale, flatten_z) -> bpy.types.Object:
    """3DFACE / SOLID - flat polygon, 3 or 4 verts."""
    mesh = bpy.data.meshes.new("DXF_Face")
    verts = []
    for attr in ("vtx0", "vtx1", "vtx2", "vtx3"):
        v = getattr(entity.dxf, attr, None)
        if v is not None:
            verts.append(tuple(_v(v, scale, flatten_z)))
    # SOLID stores verts in odd order: 0,1,3,2 -> rectangle
    if entity.dxftype() == "SOLID" and len(verts) == 4:
        verts = [verts[0], verts[1], verts[3], verts[2]]
    if len(verts) < 3:
        return None
    # De-dupe coincident verts (3DFACE often duplicates 3rd vert as 4th)
    if len(verts) == 4 and verts[2] == verts[3]:
        verts = verts[:3]
    faces = [list(range(len(verts)))]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return bpy.data.objects.new("DXF_Face", mesh)


def _text(entity, scale, flatten_z) -> bpy.types.Object:
    """TEXT / MTEXT as Blender text object."""
    txt_data = bpy.data.curves.new(name="DXF_Text", type="FONT")

    if entity.dxftype() == "MTEXT":
        txt_data.body = entity.plain_text() if hasattr(entity, "plain_text") else entity.text
        height = entity.dxf.char_height * scale
        loc = _v(entity.dxf.insert, scale, flatten_z)
    else:  # TEXT
        txt_data.body = entity.dxf.text
        height = entity.dxf.height * scale
        loc = _v(entity.dxf.insert, scale, flatten_z)

    txt_data.size = max(height, 0.001)

    obj = bpy.data.objects.new("DXF_Text", txt_data)
    obj.location = loc
    rotation = math.radians(getattr(entity.dxf, "rotation", 0.0))
    obj.rotation_euler.z = rotation
    return obj


# --- INSERT (block reference) → collection instance -------------------------
def make_block_instance(
    insert_entity,
    block_collection: bpy.types.Collection,
    scale: float,
    flatten_z: bool,
) -> bpy.types.Object:
    """Create an empty that instances the given block collection."""
    name = f"INS_{insert_entity.dxf.name}"
    obj = bpy.data.objects.new(name, None)
    obj.instance_type = "COLLECTION"
    obj.instance_collection = block_collection

    loc = _v(insert_entity.dxf.insert, scale, flatten_z)
    rot_z = math.radians(getattr(insert_entity.dxf, "rotation", 0.0))
    sx = getattr(insert_entity.dxf, "xscale", 1.0)
    sy = getattr(insert_entity.dxf, "yscale", 1.0)
    sz = getattr(insert_entity.dxf, "zscale", 1.0)

    obj.location = loc
    obj.rotation_euler = (0, 0, rot_z)
    obj.scale = (sx, sy, sz)
    return obj
