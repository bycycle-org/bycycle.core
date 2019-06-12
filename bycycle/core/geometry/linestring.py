import shapely.geometry

from .base import Base


class LineString(Base, shapely.geometry.LineString):

    @classmethod
    def string_converter(cls, string, *, converter=None):
        raise NotImplementedError
