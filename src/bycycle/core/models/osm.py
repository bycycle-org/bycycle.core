from django.contrib.gis.db import models

from bycycle.core.geometry import DEFAULT_SRID


class OsmNode(models.Model):
    class Meta:
        db_table = "osm_node"

    id = models.BigIntegerField(primary_key=True)
    is_intersection = models.BooleanField(default=False)
    geom = models.PointField(srid=DEFAULT_SRID)
