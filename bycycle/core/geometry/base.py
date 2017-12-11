from shapely import wkb, wkt
from shapely.errors import ReadingError
from shapely.geometry import mapping
from shapely.ops import transform

from .proj import DEFAULT_INPUT_SRID, DEFAULT_SRID, make_transformer


class Base:

    @classmethod
    def from_wkb(cls, value, hex=True):
        return cls(wkb.loads(value, hex=hex))

    @classmethod
    def from_wkt(cls, value):
        return cls(wkt.loads(value))

    @classmethod
    def from_string(cls, s):
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

    def reproject(self, input_srid=DEFAULT_INPUT_SRID,
                  output_srid=DEFAULT_SRID):
        """Reproject this geometry.

        By default, assume this geometry is lat/long (4326) and
        reproject it to the default projection (3857).

        """
        if input_srid == output_srid:
            return self.__class__(self)
        else:
            projector = make_transformer(input_srid, output_srid)
        return transform(projector, self)

    @property
    def lat_long(self):
        return self.reproject(DEFAULT_SRID, DEFAULT_INPUT_SRID)

    def __repr__(self):
        return self.__str__()

    def __json_data__(self):
        return mapping(self)
