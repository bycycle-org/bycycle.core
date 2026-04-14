import re

import pyproj
from django.contrib.gis.geos import GEOSGeometry
from shapely import wkt
from shapely.geometry import LineString, Point

from .proj import DEFAULT_SRID

__all__ = [
    "as_geos",
    "is_coord",
    "length_in_meters",
    "point_from_string",
    "split_line",
    "trim_line",
]


def as_geos(geom, srid=DEFAULT_SRID):
    """Convert Shapely geometry object to GEOS object.

    This is required for interoperation between Shapely and Django.

    .. todo:: Shapely objects are GEOS objects under the hood, so it
        should be possible to do this without marshaling through WKT.

    """
    return GEOSGeometry(geom.wkt, srid=srid)


def is_coord(value):
    """Is ``value`` a valid coordinate?

    Args:
        value (str): A string representing an integer or a simple float

    Returns:
        bool: Whether the string is a valid coordinate

    """
    return re.fullmatch(r"\d+(\.\d+)?", value) is not None


def length_in_meters(geom, geod=pyproj.Geod(ellps="WGS84")):
    """Get length of geometry in meters.

    Assumes ``geom`` is lat/long (4326).

    """
    distance = 0
    for c, d in zip(geom.coords[:-1], geom.coords[1:]):
        *azimuths, segment_distance = geod.inv(c[0], c[1], d[0], d[1])
        distance += segment_distance
    return distance


def point_from_string(
    string,
    *,
    string_re=re.compile(
        r" *"
        r"(?P<latitude>[+-]?\d+(?:\.\d*)?)"
        r"(?: *, *| +)"
        r"(?P<longitude>[+-]?\d+(?:\.\d*)?)"
        r" *",
    ),
    wkt_re=re.compile(
        r" *"
        r"POINT *\("
        r"[+-]?\d+(?:\.\d*)?"
        r" +"
        r"[+-]?\d+(?:\.\d*)?"
        r" *\)"
        r" *",
    ),
) -> Point | None:
    """Create point from string.

    Args:
        string (str): Point string in "<latitude>, <longitude>" (comma
            optional) or WKT format.
        string_re(re.Pattern): Regular expression pattern used to match
            "<latitude>, <longitude>" format.
        wkt_re(re.Pattern): Regular expression pattern used to match WKT
            format.

    Returns:
        Point when the string can be parsed as a point.
        None when the string cannot be parsed as a point.

    """
    if match := string_re.fullmatch(string):
        latitude = match.group("latitude")
        longitude = match.group("longitude")
        return Point(float(longitude), float(latitude))

    if wkt_re.fullmatch(string):
        point = wkt.loads(string)
        assert isinstance(point, Point)
        return point

    return None


def split_line(line, point):
    """Split linestring at point."""
    distance = line.project(point)
    coords = line.coords
    shared_coords = list(point.coords)

    coords1 = [coords[0]]
    coords2 = []

    for c in coords[1:-1]:
        p = Point(c)
        p_distance = line.project(p)
        if p_distance < distance:
            coords1.append(c)
        elif p_distance > distance:
            coords2.append(c)

    coords2.append(coords[-1])

    coords1 = coords1 + shared_coords
    coords2 = shared_coords + coords2

    return LineString(coords1), LineString(coords2)


def trim_line(line, point1, point2):
    distance1 = line.project(point1)
    distance2 = line.project(point2)
    if distance1 > distance2:
        point1, point2 = point2, point1
        distance1, distance2 = distance2, distance1
    coords = [point1]
    for c in line.coords:
        p = Point(c)
        p_distance = line.project(p)
        if distance1 <= p_distance <= distance2:
            coords.append(c)
    coords.append(point2)
    return LineString(coords)
