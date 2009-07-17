import sqlalchemy

from shapely import geometry, wkb


class Geometry(sqlalchemy.types.TypeEngine):
    """PostGIS Geometry Type."""

    def __init__(self, SRID, type_, dimension):
        super(Geometry, self).__init__()
        self.SRID = SRID
        self.type = type_.upper()
        self.dimension = dimension

    def get_col_spec(self):
        return 'GEOMETRY'

    def bind_processor(self, dialect):
        """Convert from Python type to database type."""
        def process(value):
            """``value`` is a Python/Shapely geometry object."""
            if value is None:
                return None
            else:
                return 'SRID=%s;%s' % (self.SRID, value)
        return process

    def result_processor(self, dialect):
        """Convert from database type to Python type."""
        def process(value):
            """``value`` is a hex-encoded WKB string."""
            if value is None:
                return None
            else:
                return wkb.loads(value.decode('hex'))
        return process


class POINT(Geometry):
    def __init__(self, SRID):
        super(POINT, self).__init__(SRID, 'POINT', 2)


class LINESTRING(Geometry):
    def __init__(self, SRID):
        super(LINESTRING, self).__init__(SRID, 'LINESTRING', 2)


class MULTILINESTRING(Geometry):
    def __init__(self, SRID):
        super(MULTILINESTRING, self).__init__(SRID, 'MULTILINESTRING', 2)


class MULTIPOLYGON(Geometry):
    def __init__(self, SRID):
        super(MULTIPOLYGON, self).__init__(SRID, 'MULTIPOLYGON', 2)
