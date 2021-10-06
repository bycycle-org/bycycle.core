from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import BigInteger, Boolean, Float, Integer, String

from tangled.decorators import cached_property

from bycycle.core.geometry import DEFAULT_SRID, length_in_meters
from bycycle.core.geometry.sqltypes import LINESTRING
from bycycle.core.model import Base

from .intersection import Intersection


class Street(Base):

    __tablename__ = 'street'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    osm_id = Column(BigInteger)
    osm_seq = Column(Integer)
    geom = Column(LINESTRING(DEFAULT_SRID))

    start_node_id = Column(BigInteger, ForeignKey(Intersection.id), nullable=True)
    end_node_id = Column(BigInteger, ForeignKey(Intersection.id), nullable=True)

    base_cost = Column(Float, nullable=True)

    # Tags
    name = Column(String)
    description = Column(String)
    highway = Column(String)
    bicycle = Column(String)
    cycleway = Column(String)
    oneway = Column(Boolean)
    oneway_bicycle = Column(Boolean)

    start_node = relationship(Intersection, primaryjoin=(start_node_id == Intersection.id), viewonly=True)
    end_node = relationship(Intersection, primaryjoin=(end_node_id == Intersection.id), viewonly=True)

    # From https://wiki.openstreetmap.org/wiki/Key:highway
    road_types = (
        'motorway',
        'trunk',
        'primary',
        'secondary',
        'tertiary',
        'unclassified',
        'residential',
    )

    path_types = (
        'cycleway',
        'footway',
        'living_street',
        'path',
        'pedestrian',
    )

    routable_types = road_types + path_types + (
        'motorway_link',
        'trunk_link',
        'primary_link',
        'secondary_link',
        'tertiary_link',
    )

    bicycle_allowed_types = (
        'designated',
        'yes',
    )

    @cached_property
    def is_routable(self):
        return self.bicycle in self.bicycle_allowed_types or self.highway in self.routable_types

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
        return self.name or self.description or f'[{self.highway}]'

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

    if bicycle == 'no':
        return None

    if highway == 'cycleway' or cycleway == 'track':
        # Both of these indicate cycle tracks, which we consider the
        # baseline--everything else is more expensive.
        pass
    else:
        if highway == 'residential':
            cost *= 1.1
        elif highway == 'unclassified':
            cost *= 1.2
        elif highway in ('tertiary', 'tertiary_link'):
            cost *= 1.4
        elif highway in ('secondary', 'secondary_link'):
            cost *= 1.8
        elif highway == 'primary':
            cost *= 2.6
        elif highway in ('trunk', 'service'):
            cost *= 4.2
        elif highway in ('motorway', 'motorway_link'):
            cost *= 7.4
        elif highway in ('footway', 'living_street', 'path', 'pedestrian'):
            # Avoid pedestrians when possible
            cost *= 2.6
        else:
            # Be conservative and avoid unknown types
            return None

        if cycleway == 'lane':
            # Makes a residential street with a bike lane equivalent to
            # a cycle track.
            cost *= 0.91
        elif cycleway == 'shared_lane':
            cost *= 0.91
        elif bicycle == 'avoid':
            cost *= 4
        elif bicycle == 'designated' and cycleway != 'proposed':
            # NOTE: It's not clear exactly what "designated" means in
            #       OSM because there are a lot of "designated" streets
            #       that don't correspond to the official bike network.
            cost *= 0.95

    return cost
