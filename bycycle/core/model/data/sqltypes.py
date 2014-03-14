from sqlalchemy.types import UserDefinedType

from shapely import wkb


class Geometry(UserDefinedType):

    """PostGIS Geometry Type."""

    def __init__(self, srid, type_=None):
        self.type = type_ or self.__class__.__name__
        self.srid = srid

    def get_col_spec(self):
        return 'GEOMETRY({0.type}, {0.srid})'.format(self)

    def bind_processor(self, dialect):
        """Convert from Python type to database type."""
        def process(value):
            """``value`` is a Python/Shapely geometry object."""
            if value is None:
                return None
            else:
                return 'SRID={};{}'.format(self.srid, value)
        return process

    def result_processor(self, dialect, coltype):
        """Convert from database type to Python type."""
        def process(value):
            """``value`` is a hex-encoded WKB string."""
            if value is None:
                return None
            else:
                return wkb.loads(value, hex=True)
        return process


class POINT(Geometry):

    pass


class LINESTRING(Geometry):

    pass


class MULTILINESTRING(Geometry):

    pass


class MULTIPOLYGON(Geometry):

    pass
