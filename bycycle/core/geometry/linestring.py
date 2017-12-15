import shapely.geometry

from tangled.converters import as_seq_of_seq

from .base import Base


class LineString(Base, shapely.geometry.LineString):

    @classmethod
    def string_converter(cls, string, *,
                         converter=as_seq_of_seq(
                             sep=';',
                             type_=tuple, item_sep=',',
                             line_type=tuple, item_converter=float
                         )):
        """Convert string to list of coordinates.

        Used by :meth:`Base.from_string`.

        Args:
            string (str): A string like 'x1, y1; x2, y2; ...'
            converter: Splits string into a list of coordinates

        Returns:
            Tuple of tuples of floats: ((x, y), ...)

        Raises:
            ValueError: When the string can't be parsed

        """
        line = converter(string)
        num = len(line)
        if num < 2:
            raise ValueError('Expected at least two coordinate pairs; got %s' % num)
        for coordinates in line:
            num = len(coordinates)
            if num != 2:
                raise ValueError('Expected two coordinates; got %s' % num)
        return line
