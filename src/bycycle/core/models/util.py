from dataclasses import dataclass

from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import GeoFunc
from django.db.models.expressions import RawSQL

from shapely import wkb


@dataclass
class ExtentInfo:
    bbox: tuple[float, float, float, float]
    boundary: tuple[float, ...]
    center: tuple[float, ...]


class ST_Envelope(GeoFunc):
    function = "ST_Envelope"


class ST_Extent(GeoFunc):
    function = "ST_Extent"


def get_extent(model: models.Model, field="geom") -> ExtentInfo:
    """Get extent info for ORM model or table.

    Args:
        model: ORM model
        field: model field to query for extent

    Returns:
        ExtentInfo

    """
    result = model.objects.annotate(extent=RawSQL(f"ST_Envelope(ST_Extent({field}))"))
    extent = wkb.loads(result.extent, hex=True)
    bbox = extent.bounds
    boundary = extent.boundary.coords
    center = extent.centroid.coords[0]
    return ExtentInfo(bbox, boundary, center)
