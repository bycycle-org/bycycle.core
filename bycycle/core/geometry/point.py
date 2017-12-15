import shapely.geometry

from tangled.converters import as_tuple_of

from .base import Base


class Point(Base, shapely.geometry.Point):

    @classmethod
    def string_converter(cls, string, *, converter=as_tuple_of(float, sep=',')):
        """Convert string to coordinates.

        Used by :meth:`Base.from_string`.

        Args:
            string (str): A string like 'x, y'
            converter: Splits string into coordinates

        Returns:
            Tuple of floats: (x, y)

        Raises:
            ValueError: When the string can't be parsed

        """
        coordinates = converter(string)
        num = len(coordinates)
        if num != 2:
            raise ValueError('Expected two coordinates; got %s' % num)
        return coordinates
