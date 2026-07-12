#
#  kipy_shapely.py
#
#  Conversion helpers between kicad-python (kipy) geometry and shapely.
#
#  All coordinates are kept in KiCad IPC API units (nanometers).
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

import math

from kipy.geometry import (
    Vector2,
    arc_center,
    arc_radius,
    arc_start_angle,
    arc_end_angle,
)
from shapely.geometry import LineString, Point, Polygon
from shapely.validation import make_valid

ARC_SEGMENT_ANGLE = math.radians(5)


def sample_arc(start, mid, end):
    """Approximate an arc given by start/mid/end points with a point list."""
    center = arc_center(start, mid, end)
    if center is None:
        return [(start.x, start.y), (mid.x, mid.y), (end.x, end.y)]
    radius = arc_radius(start, mid, end)
    a0 = arc_start_angle(start, mid, end)
    a1 = arc_end_angle(start, mid, end)
    if a0 is None or a1 is None:
        return [(start.x, start.y), (mid.x, mid.y), (end.x, end.y)]
    # KiCad arcs go counter-clockwise from start to end angle
    while a1 < a0:
        a1 += 2 * math.pi
    steps = max(2, int(math.ceil((a1 - a0) / ARC_SEGMENT_ANGLE)))
    return [
        (
            center.x + radius * math.cos(a0 + (a1 - a0) * i / steps),
            center.y + radius * math.sin(a0 + (a1 - a0) * i / steps),
        )
        for i in range(steps + 1)
    ]


def polyline_to_points(polyline):
    """Convert a kipy PolyLine to a list of (x, y) tuples, sampling arcs."""
    points = []
    for node in polyline.nodes:
        if node.has_point:
            points.append((node.point.x, node.point.y))
        elif node.has_arc:
            arc = node.arc
            points.extend(sample_arc(arc.start, arc.mid, arc.end))
    return points


def polygon_to_shapely(polygon_with_holes):
    """Convert a kipy PolygonWithHoles to a shapely Polygon."""
    outline = polyline_to_points(polygon_with_holes.outline)
    if len(outline) < 3:
        return None
    holes = []
    for hole in polygon_with_holes.holes:
        hole_points = polyline_to_points(hole)
        if len(hole_points) >= 3:
            holes.append(hole_points)
    poly = Polygon(outline, holes)
    if not poly.is_valid:
        poly = make_valid(poly)
    return poly


def zone_outline_to_shapely(zone):
    """Convert a kipy Zone outline to a shapely Polygon."""
    try:
        return polygon_to_shapely(zone.outline)
    except (IndexError, ValueError):
        return None


def board_shape_to_shapely(shape):
    """Convert a kipy BoardShape (graphic item, e.g. on Edge.Cuts) to a
    shapely geometry describing its drawn path.

    Works on the protobuf level because the concrete kipy shape wrappers
    do not expose a common geometry interface. Returns None for
    unsupported shapes.
    """
    proto = shape.proto
    # BoardGraphicShape wraps the actual GraphicShape (with the
    # "geometry" oneof) in its "shape" field
    geo = proto.shape if hasattr(proto, "shape") else proto
    kind = geo.WhichOneof("geometry")
    try:
        if kind == "segment":
            seg = geo.segment
            return LineString(
                [(seg.start.x_nm, seg.start.y_nm), (seg.end.x_nm, seg.end.y_nm)]
            )
        if kind == "rectangle":
            rect = geo.rectangle
            x0, y0 = rect.top_left.x_nm, rect.top_left.y_nm
            x1, y1 = rect.bottom_right.x_nm, rect.bottom_right.y_nm
            return LineString([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
        if kind == "circle":
            circle = geo.circle
            center = Point(circle.center.x_nm, circle.center.y_nm)
            radius = math.hypot(
                circle.radius_point.x_nm - circle.center.x_nm,
                circle.radius_point.y_nm - circle.center.y_nm,
            )
            return center.buffer(radius).exterior
        if kind == "arc":
            arc = geo.arc
            return LineString(
                sample_arc(
                    Vector2.from_xy(arc.start.x_nm, arc.start.y_nm),
                    Vector2.from_xy(arc.mid.x_nm, arc.mid.y_nm),
                    Vector2.from_xy(arc.end.x_nm, arc.end.y_nm),
                )
            )
        if kind == "polygon":
            points = []
            for poly in geo.polygon.polygons:
                for node in poly.outline.nodes:
                    if node.HasField("point"):
                        points.append((node.point.x_nm, node.point.y_nm))
            if len(points) >= 3:
                points.append(points[0])
                return LineString(points)
    except (AttributeError, ValueError):
        return None
    return None


def track_to_shapely(track):
    """Convert a kipy Track/ArcTrack to a shapely line along its centerline."""
    if hasattr(track, "mid"):  # ArcTrack
        return LineString(sample_arc(track.start, track.mid, track.end))
    return LineString([(track.start.x, track.start.y), (track.end.x, track.end.y)])
