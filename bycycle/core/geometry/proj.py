from functools import partial

import pyproj


__all__ = [
    'DEFAULT_INPUT_SRID',
    'DEFAULT_SRID',
    'default_projector',
    'inverse_projector',
]


DEFAULT_SRID = 3857
DEFAULT_INPUT_SRID = 4326
default_projector = pyproj.Proj(init='epsg:{}'.format(DEFAULT_SRID))
inverse_projector = partial(default_projector, inverse=True)


def make_transformer(input_srid, output_srid):
    return partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:{}'.format(input_srid)),
        pyproj.Proj(init='epsg:{}'.format(output_srid)),
    )
