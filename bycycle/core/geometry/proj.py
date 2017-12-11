from functools import lru_cache, partial

import pyproj


__all__ = [
    'DEFAULT_INPUT_SRID',
    'DEFAULT_SRID',
    'make_transformer',
]


DEFAULT_INPUT_SRID = 4326
DEFAULT_SRID = 3857


@lru_cache()
def make_transformer(input_srid, output_srid):
    return partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:{}'.format(input_srid)),
        pyproj.Proj(init='epsg:{}'.format(output_srid)),
    )
