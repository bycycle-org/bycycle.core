from sqlalchemy import func, select, Column, ForeignKey
from sqlalchemy.orm import object_session, relationship
from sqlalchemy.types import CHAR, Integer
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from shapely import geometry, wkt
from shapely.geometry.base import BaseGeometry

from bycycle.core.util import joinAttrs
from bycycle.core.model.db import engine, metadata


__all__ = ['Base', 'Node', 'Edge']


class Entity(object):

    pass


Base = declarative_base(metadata=metadata, cls=Entity)


class Node(object):

    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)

    @property
    def edges(self):
        return list(self.edges_f) + list(self.edges_t)


class Edge(object):

    __tablename__ = 'edges'

    id = Column(Integer, primary_key=True)
    addr_min = Column(Integer)
    addr_max = Column(Integer)
    addr_f_l = Column(Integer)
    addr_f_r = Column(Integer)
    addr_t_l = Column(Integer)
    addr_t_r = Column(Integer)
    even_side = Column(CHAR(1))
    one_way = Column(Integer)

    @declared_attr
    def street_name_id(self):
        return Column(Integer, ForeignKey('street_names.id'))

    @declared_attr
    def place_l_id(self):
        return Column(Integer, ForeignKey('places.id'))

    @declared_attr
    def place_r_id(self):
        return Column(Integer, ForeignKey('places.id'))

    @declared_attr
    def street_name(self):
        return relationship('StreetName', cascade='all')

    @declared_attr
    def place_l(self):
        return relationship(
            'Place', primaryjoin='Edge.place_l_id == Place.id', cascade='all')

    @declared_attr
    def place_r(self):
        return relationship(
            'Place', primaryjoin='Edge.place_r_id == Place.id', cascade='all')

    def to_feet(self):
        return self.geom.length

    def to_miles(self):
        return self.geom.length * 5280.0

    def to_kilometers(self):
        return self.to_miles() * 1.609344

    def to_meters(self):
        return self.to_kilometers() / 1000.0

    def getSideNumberIsOn(self, num):
        """Determine which side of the edge, "l" or "r", ``num`` is on."""
        odd_side = 'r' if self.even_side == 'l' else 'l'
        # FIXME: What if there's no address range on the side ``num`` is on?
        #        Right now, we return the odd side by default
        return odd_side if int(num) % 2 else self.even_side

    def getPlaceOnSideNumberIsOn(self, num):
        """Get `Place` on side ``num`` is on."""
        side = self.getSideNumberIsOn(num)
        if side == 'l':
            return self.place_l
        else:
            return self.place_r

    def __len__(self):
        """Get the length of this `Edge`, using cached value if available."""
        try:
            self._length
        except AttributeError:
            self._length = self.geom.length
        return self._length

    length = __len__

    def getPointAndLocationOfNumber(self, num):
        """

        ``num``
            A number that should be in the this edge's address range

        return
            ``Point``
                The coordinate of ``num`` within this edge
            Location
                The location, in range [0, 1], of ``num`` within this edge

        """
        # Sanity check; num should always be an `int`
        num = int(num or 0)

        # Determine location in [0, 1] of num along edge
        # Note: addrs might be NULL/None
        if (not num or None in (self.addr_min, self.addr_max) or
                num < self.addr_min or num > self.addr_max):
            location = .5
        else:
            if self.addr_min == self.addr_max:
                location = .5
            else:
                edge_len = self.addr_max - self.addr_min
                dist_from_min_addr = num - self.addr_min
                location = dist_from_min_addr / edge_len

        # Function to get interpolated point
        c = self.__table__.c
        f = func.st_line_interpolate_point(c.geom, location)
        # Function to get WKT version of lat/long
        f = func.st_astext(f)

        # Query DB and get WKT POINT
        bind = object_session(self).bind
        select_ = select([f.label('wkt_point')], c.id == self.id, bind=bind)
        result = select_.execute()
        wkt_point = result.fetchone().wkt_point

        point = wkt.loads(wkt_point)
        return point, location

    def splitAtGeocode(self, geocode, node_id=-1, edge_f_id=-1, edge_t_id=-2):
        """Split this edge at ``geocode`` and return two new edges.

        ``geocode`` `Geocode` -- The geocode to split the edge at.

        See `splitAtLocation` for further details

        """
        edge_f, edge_t = self.splitAtLocation(
            geocode.xy, geocode.location, node_id, edge_f_id, edge_t_id
        )
        # address range
        num = geocode.address.number
        edge_f.addr_t_l, edge_f.addr_t_r = num, num
        edge_t.addr_f_l, edge_t.addr_f_r = num, num
        return edge_f, edge_t

    def splitAtNumber(self, num, node_id=-1, edge_f_id=-1, edge_t_id=-2):
        """Split this edge at ``num`` and return two new edges.

        ``num`` `int` -- The address number to split the edge at.

        See `splitAtLocation` for further details

        """
        point, location = self.getPointAndLocationOfNumber(num)
        return self.splitAtLocation(
            point, location, node_id, edge_f_id, edge_t_id
        )

    def splitAtLocation(self, point, location,
                        node_id=-1, edge_f_id=-1, edge_t_id=-2):
        """Split this edge at ``location`` and return two new edges.

        The first edge is `node_f`=>``num``; the second is ``num``=>`node_t`.
        Distribute attributes of original edge to the two new edges.

        ``point`` `Geometry` -- Point at location
        ``location`` `float` -- Location in range [0, 1] to split at
        ``node_id`` -- Node ID to assign the node at the split
        ``edge_f_id`` -- Edge ID to assign the `node_f`=>``num`` edge
        ``edge_t_id`` -- Edge ID to assign the ``num``=>`node_t` edge

        return `Edge`, `Edge` -- `node_f`=>``num``, ``num``=>`node_t` edges

        Recipe:
        - Determine location of num along edge; use .5 as default
        - Get XY at location
        - Get line geometry on either side of XY
        - Transfer geometry and attributes to two new edges
        - Return the  two new edges

        """
        Point = geometry.Point

        point = (point.x, point.y)
        points = list(self.geom.coords)
        num_points = len(points)
        N = int(num_points * location) or 1
        if N == num_points:
            N -= 1
        edge_f_points = points[:N] + [point]
        edge_t_points = [point] + points[N:]
        edge_f_geom = geometry.LineString(edge_f_points)
        edge_t_geom = geometry.LineString(edge_t_points)

        RegionNode = self.node_f.__class__
        shared_node = RegionNode(id=node_id, geom=Point(points[N]))

        edge_f = self.clone(
            id=edge_f_id,
            addr_f_l=self.addr_f_l,
            addr_f_r=self.addr_f_r,
            node_f_id=self.node_f_id,
            node_f=RegionNode(id=self.node_f_id, geom=Point(points[0])),
            node_t_id=node_id,
            node_t=shared_node,
            geom=edge_f_geom,
        )

        edge_t = self.clone(
            id=edge_t_id,
            addr_t_l=self.addr_t_l,
            addr_t_r=self.addr_t_r,
            node_f_id=node_id,
            node_f=shared_node,
            node_t_id=self.node_t_id,
            node_t=RegionNode(id=self.node_t_id, geom=Point(points[-1])),
            geom=edge_t_geom,
        )

        return edge_f, edge_t

    def clone(self, **override_attrs):
        keys = [c.key for c in self.__mapper__.columns]
        keys += [r.key for r in self.__mapper__.relationships]
        attrs = {k: getattr(self, k) for k in keys}
        attrs.update(override_attrs)
        return self.__class__(**attrs)

    def __str__(self):
        stuff = [
            joinAttrs(('Address Range:',
                       self.addr_f_l, ', ', self.addr_f_r,
                       'to',
                       self.addr_t_l, ', ', self.addr_t_r)),
            (self.street_name or '[No Street Name]'),
            self.place_l, self.place_r,
        ]
        return joinAttrs(stuff, join_string='\n')

    def to_simple_object(self, fields=None):
        return super(Edge, self).to_simple_object(fields=fields)
