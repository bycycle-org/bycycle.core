import re

from .linestring import LineString
from .point import Point
from .proj import *


def is_coord(value):
    """Is ``value`` a valid coordinate?

    Args:
        value (str): A string representing an integer or a simple float

    Returns:
        bool: Whether the string is a valid coordinate

    """
    return re.fullmatch(r'\d+(\.\d+)?', value) is not None


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
