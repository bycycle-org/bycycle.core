import re

import shapely.geometry

from .base import Base


class Point(Base, shapely.geometry.Point):

    string_re = (
        r' *'
        r'(?P<lat>[+-]?\d+(\.\d*)?)'
        r'(?: *, *| +)'
        r'(?P<long>[+-]?\d+(\.\d*)?)'
        r' *'
    )

    @classmethod
    def string_converter(cls, string):
        """Convert string to coordinates.

        Used by :meth:`Base.from_string`.

        Args:
            string (str): A lat/long string like '45.5, -122.5'

        Returns:
            tuple: (long, lat)

        Raises:
            ValueError: When the string can't be parsed

        """
        match = re.fullmatch(cls.string_re, string)

        if match:
            coordinates = [match.group('long'), match.group('lat')]
            coordinates = [float(c) for c in coordinates]
        else:
            raise ValueError('String does not match expected point format')

        return coordinates
