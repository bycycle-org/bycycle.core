from functools import lru_cache

import pyproj


__all__ = [
    'DEFAULT_INPUT_SRID',
    'DEFAULT_SRID',
    'make_projector',
]


DEFAULT_INPUT_SRID = 4326
DEFAULT_SRID = 3857


@lru_cache()
def make_projector(input_srid=DEFAULT_INPUT_SRID, output_srid=DEFAULT_SRID):
    from_proj = pyproj.Proj(init='epsg:{}'.format(input_srid))
    to_proj = pyproj.Proj(init='epsg:{}'.format(output_srid))
    transformer = pyproj.Transformer.from_proj(from_proj, to_proj)
    return transformer.transform
