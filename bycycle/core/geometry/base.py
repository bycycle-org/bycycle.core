from shapely import wkb, wkt
from shapely.errors import ReadingError
from shapely.geometry import mapping

from .proj import DEFAULT_SRID, WEB_SRID, make_projector, reproject


class Base:

    @classmethod
    def from_wkb(cls, value, hex=True):
        return cls(wkb.loads(value, hex=hex))

    @classmethod
    def from_wkt(cls, value):
        # This looks-like-wkt business keeps Shapely from printing a
        # warning for non-WKT strings, which it does even though it
        # raises an exception.
        looks_like_wkt = value.startswith(cls.__name__.upper())
        return cls(wkt.loads(value)) if looks_like_wkt else None

    @classmethod
    def from_string(cls, s):
        """Create a geometry object from a type-appropriate string.

        E.g., for a point, the string could be a well-known text string
        like ``POINT(-122.5 45.5)`` or a string like ``45.5, -122.5``.

        """
        try:
            coords = cls.string_converter(s)
        except ValueError:
            try:
                geom = cls.from_wkt(s)
            except ReadingError:
                geom = None
        else:
            geom = cls(coords)

        if geom is not None:
            return geom

        raise ValueError(
            'cannot create {} from string: {}'
            .format(geom.__class__.__name__, s))

    def reproject(self, input_srid=DEFAULT_SRID, output_srid=WEB_SRID):
        """Reproject this geometry.

        By default, assume this geometry is lat/long (4326) and
        reproject it to web mercator (3857).

        """
        if (input_srid, output_srid) == (DEFAULT_SRID, WEB_SRID):
            return reproject(self)
        projector = make_projector(input_srid, output_srid)
        return reproject(self, projector)

    def __repr__(self):
        return self.__str__()

    def __json__(self, request):
        return mapping(self)
