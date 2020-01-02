import re

import pyproj

from bycycle.core.geometry import Point, LineString


__all__ = ['is_coord', 'length_in_meters', 'split_line', 'trim_line']


def is_coord(value):
    """Is ``value`` a valid coordinate?

    Args:
        value (str): A string representing an integer or a simple float

    Returns:
        bool: Whether the string is a valid coordinate

    """
    return re.fullmatch(r'\d+(\.\d+)?', value) is not None


def length_in_meters(geom, geod=pyproj.Geod(ellps='WGS84')):
    """Get length of geometry in meters.

    Assumes ``geom`` is lat/long (4326).

    """
    distance = 0
    for c, d in zip(geom.coords[:-1], geom.coords[1:]):
        *azimuths, segment_distance = geod.inv(c[0], c[1], d[0], d[1])
        distance += segment_distance
    return distance


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
