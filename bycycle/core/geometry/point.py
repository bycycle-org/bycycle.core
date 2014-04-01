import shapely.geometry

from tangled.converters import as_tuple_of


from .base import Base


class Point(Base, shapely.geometry.Point):

    string_converter = as_tuple_of(float, sep=',')
    """Allows conversion of strings of the form '{x}, {y}'.

    Used by :meth:`Base.from_string`.

    """
