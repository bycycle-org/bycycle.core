###############################################################################
# $Id$
# Created 2007-05-07.
#
# Abstract database entity classes.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Abstract database entity classes.

They are "abstract" in the sense that they are not intended to be used
directly. Instead they are overridden by inheriting with ``inheritance=None``
and calling ``base_statements`` first in the subclass definition.

"""
import sys

from sqlalchemy import func, select, Column, ForeignKey
from sqlalchemy.orm import relation
from sqlalchemy.types import Integer, String, CHAR, Integer
from sqlalchemy.ext.declarative import declarative_base

from shapely import geometry, wkt

import simplejson

from byCycle.util import gis, joinAttrs
from byCycle.model.db import engine, metadata, Session
from byCycle.model.entities.util import cascade_arg


__all__ = ['DeclarativeBase', 'Node', 'Edge']


class Entity(object):
    @classmethod
    def q(cls):
        return Session.query(cls)

    @classmethod
    def columns(cls):
        return cls.__table__.columns

    @classmethod
    def all(cls):
        return cls.q().all()

    @classmethod
    def get(cls, id_or_ids):
        if isinstance(id_or_ids, (list, tuple, set)):
            return cls.q().filter(cls.id.in_(id_or_ids)).all()
        else:
            return cls.q().get(id_or_ids)

    @classmethod
    def get_by_slug(cls, slug, unique=False):
        return cls.get_by('slug', slug, unique=True)

    @classmethod
    def get_by(cls, col, values, unique=False):
        """Get objects keyed on ``col`` and having the given ``values``.

        ``col``
            A column name

        ``values``
            A single value or sequence (`list` or `tuple`) of values.

        ``unique``
            Whether or not we expect a single value to be returned. Corresponds
            to a UNIQUE index.

        """
        if not isinstance(values, (tuple, list)):
            values = [values]
        q = cls.q().filter(getattr(cls, col).in_(values))
        if unique:
            result = q.one()
        else:
            objects = q.all()
            result = objects[0] if len(objects) == 1 else objects
        return result

    def to_simple_object(self):
        """Return an object that can be serialized by ``simplejson.dumps``."""
        obj = dict(type=self.__class__.__name__)
        attrs = set(self._attrs)
        try:
            self.__table__
        except AttributeError:
            pass
        else:
            attrs = attrs.union(set(self.__table__.columns.keys()))
        for name in attrs:
            value = getattr(self, name)
            try:
                value = value.to_simple_object()
            except AttributeError:
                pass
            obj[name] = value
        return obj

    def to_json(self):
        return simplejson.dumps(self.to_simple_object())

    @staticmethod
    def to_json_collection(instances):
        simple_obj = {'result': [i.to_simple_object() for i in instances]}
        return simplejson.dumps(simple_obj)

    def __setattr__(self, name, value):
        # TODO: Apparently, objects aren't ``__init__'d`` when they're pulled
        #  from the DB. There's probably a better place for this
        # initialization of ``_attrs``.
        try:
            self._attrs
        except AttributeError:
            self.__dict__['_attrs'] = set()
        super(Entity, self).__setattr__(name, value)
        if not name.startswith('_'):
            self._attrs.add(name)

    def __repr__(self):
        try:
            self.__table__
        except AttributeError:
            return object.__repr__(self)
        else:
            return str(self.to_simple_object())


DeclarativeBase = declarative_base(metadata=metadata, cls=Entity)


class Node(DeclarativeBase):
    __tablename__ = 'nodes'
    __table_args__ = dict(schema='public')

    id = Column(Integer, primary_key=True)
    type = Column('type', String(50))

    __mapper_args__ = {'polymorphic_on': type}

    region_id = Column(Integer, ForeignKey('regions.id'))

    region = relation('Region', cascade='all')
    edges_f = relation('Edge', primaryjoin='Node.id == Edge.node_f_id')
    edges_t = relation('Edge', primaryjoin='Node.id == Edge.node_t_id')

    @property
    def edges(self):
        return list(self.edges_f) + list(self.edges_t)


class Edge(DeclarativeBase):
    __tablename__ = 'edges'
    __table_args__ = dict(schema='public')

    id = Column(Integer, primary_key=True)
    type = Column('type', String(50))
    addr_f_l = Column(Integer)
    addr_f_r = Column(Integer)
    addr_t_l = Column(Integer)
    addr_t_r = Column(Integer)
    even_side = Column(CHAR(1))
    one_way = Column(Integer)

    __mapper_args__ = {'polymorphic_on': type}

    region_id = Column(Integer, ForeignKey('regions.id'))
    node_f_id = Column(Integer, ForeignKey('public.nodes.id'))
    node_t_id = Column(Integer, ForeignKey('public.nodes.id'))
    street_name_id = Column(Integer, ForeignKey('street_names.id'))
    place_l_id = Column(Integer, ForeignKey('places.id'))
    place_r_id = Column(Integer, ForeignKey('places.id'))

    region = relation('Region', cascade='all')
    node_f = relation(
        'Node', primaryjoin='Edge.node_f_id == Node.id', cascade=cascade_arg)
    node_t = relation(
        'Node', primaryjoin='Edge.node_t_id == Node.id', cascade=cascade_arg)
    street_name = relation('StreetName', cascade=cascade_arg)
    place_l = relation(
        'Place', primaryjoin='Edge.place_l_id == Place.id', cascade=cascade_arg)
    place_r = relation(
        'Place', primaryjoin='Edge.place_r_id == Place.id', cascade=cascade_arg)

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
        addrs = (self.addr_f_l, self.addr_f_r, self.addr_t_l, self.addr_t_r)
        min_addr = min(addrs)
        max_addr = max(addrs)
        if not num or None in (min_addr, max_addr):
            location = .5
        else:
            if min_addr == max_addr:
                location = .5
            else:
                edge_len = max_addr - min_addr
                dist_from_min_addr = num - min_addr
                location = float(dist_from_min_addr) / edge_len

        _Edge = self.region.module.Edge

        # Function to get interpolated point
        c = _Edge.__table__.c
        f = func.line_interpolate_point(c.geom, location)
        # Function to get WKT version of lat/long
        f = func.astext(f)

        # Query DB and get WKT POINT
        select_ = select([f.label('wkt_point')], c.id == self.id, bind=engine)
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

        RegionEdge = self.__class__
        edge_f = RegionEdge(id=edge_f_id,
                            node_f_id=self.node_f_id, node_t_id=node_id,
                            street_name=self.street_name,
                            geom=edge_f_geom)
        edge_t = RegionEdge(id=edge_t_id,
                            node_f_id=node_id, node_t_id=self.node_t_id,
                            street_name=self.street_name,
                            geom=edge_t_geom)

        RegionNode = self.node_f.__class__
        shared_node = RegionNode(id=node_id, geom=Point(points[N]))
        edge_f.node_f = RegionNode(id=self.node_f_id, geom=Point(points[0]))
        edge_f.node_t = shared_node
        edge_t.node_f = shared_node
        edge_t.node_t = RegionNode(id=self.node_t_id, geom=Point(points[-1]))

        return edge_f, edge_t

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

    def to_simple_object(self):
        return super(Edge, self).to_simple_object()
