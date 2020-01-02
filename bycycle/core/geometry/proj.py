from functools import lru_cache

import pyproj

from shapely.ops import transform


__all__ = [
    'DEFAULT_SRID',
    'WEB_SRID',
    'make_projector',
    'reproject',
]


DEFAULT_SRID = 4326
WEB_SRID = 3857


@lru_cache()
def make_projector(input_srid=DEFAULT_SRID, output_srid=WEB_SRID):
    from_proj = pyproj.Proj(init='epsg:{}'.format(input_srid))
    to_proj = pyproj.Proj(init='epsg:{}'.format(output_srid))
    transformer = pyproj.Transformer.from_proj(from_proj, to_proj)
    return transformer.transform


def reproject(geom, projector=make_projector()):
    """Reproject geometry.

    By default, the geometry will be transformed from lat/long (4326) to
    web mercator (3857).

    """
    return transform(projector, geom)
