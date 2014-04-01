import shapely.geometry

from tangled.converters import as_seq_of_seq

from .base import Base


class LineString(Base, shapely.geometry.LineString):

    string_converter = as_seq_of_seq(sep=';', item_sep=',', item_converter=float)
    """Allows conversion of strings of the form '{x1}, {y1}; {x2}, {y2}'.

    Used by :meth:`Base.from_string`.

    """
