from functools import cached_property

from django.contrib.gis.db import models

from bycycle.core.geometry import DEFAULT_SRID, length_in_meters

from .intersection import Intersection


class Street(models.Model):
    class Meta:
        db_table = "street"

    id = models.BigAutoField(primary_key=True)

    osm_id = models.BigIntegerField()
    osm_seq = models.IntegerField()

    geom = models.LineStringField(srid=DEFAULT_SRID)

    start_node = models.ForeignKey(
        Intersection,
        # Adds a property to the Intersection model named start_streets
        # that includes all the streets that start at this node.
        related_name="start_streets",
        on_delete=models.CASCADE,
    )

    end_node = models.ForeignKey(
        Intersection,
        # Adds a property to the Intersection model named end_streets
        # that includes all the streets that end at this node.
        related_name="end_streets",
        on_delete=models.CASCADE,
    )

    base_cost = models.FloatField(null=True)

    # Tags
    name = models.TextField(null=True)
    description = models.TextField(null=True)
    highway = models.TextField(null=True)
    bicycle = models.TextField(null=True)
    cycleway = models.TextField(null=True)
    oneway = models.BooleanField(null=True)
    oneway_bicycle = models.BooleanField(null=True)

    # From https://wiki.openstreetmap.org/wiki/Key:highway
    road_types = (
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "unclassified",
        "residential",
    )

    path_types = (
        "cycleway",
        "footway",
        "living_street",
        "path",
        "pedestrian",
    )

    routable_types = (
        road_types
        + path_types
        + (
            "motorway_link",
            "trunk_link",
            "primary_link",
            "secondary_link",
            "tertiary_link",
        )
    )

    bicycle_allowed_types = (
        "designated",
        "yes",
    )

    @cached_property
    def is_routable(self):
        return (
            self.bicycle in self.bicycle_allowed_types
            or self.highway in self.routable_types
        )

    @cached_property
    def meters(self):
        return length_in_meters(self.geom)

    @cached_property
    def kilometers(self):
        return self.meters * 0.001

    @cached_property
    def feet(self):
        return self.meters * 3.28084

    @cached_property
    def miles(self):
        return self.meters * 0.0006213712

    @cached_property
    def display_name(self):
        return self.name or self.description or f"[{self.highway}]"

    def clone(self, **override_attrs):
        keys = [c.key for c in self.__mapper__.columns]
        keys += [r.key for r in self.__mapper__.relationships]
        attrs = {k: getattr(self, k) for k in keys}
        attrs.update(override_attrs)
        return self.__class__(**attrs)

    def __str__(self):
        return self.display_name


def base_cost(geom, highway, bicycle, cycleway, **attrs):
    cost = length_in_meters(geom)

    if bicycle == "no":
        return None

    if highway == "cycleway" or cycleway == "track":
        # Both of these indicate cycle tracks, which we consider the
        # baseline--everything else is more expensive.
        pass
    else:
        if highway == "residential":
            cost *= 1.1
        elif highway == "unclassified":
            cost *= 1.2
        elif highway in ("tertiary", "tertiary_link"):
            cost *= 1.4
        elif highway in ("secondary", "secondary_link"):
            cost *= 1.8
        elif highway == "primary":
            cost *= 2.6
        elif highway in ("trunk", "service"):
            cost *= 4.2
        elif highway in ("motorway", "motorway_link"):
            cost *= 7.4
        elif highway in ("footway", "living_street", "path", "pedestrian"):
            # Avoid pedestrians when possible
            cost *= 2.6
        else:
            # Be conservative and avoid unknown types
            return None

        if cycleway == "lane":
            # Makes a residential street with a bike lane equivalent to
            # a cycle track.
            cost *= 0.91
        elif cycleway == "shared_lane":
            cost *= 0.91
        elif bicycle == "avoid":
            cost *= 4
        elif bicycle == "designated" and cycleway != "proposed":
            # NOTE: It's not clear exactly what "designated" means in
            #       OSM because there are a lot of "designated" streets
            #       that don't correspond to the official bike network.
            cost *= 0.95

    return cost
