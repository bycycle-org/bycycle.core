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

from elixir.statements import STATEMENTS
from elixir import Entity
from elixir import has_field, belongs_to, has_many
from elixir import Integer, String, CHAR, Integer

from sqlalchemy import func, select

from cartography import geometry

from byCycle.util import gis, joinAttrs
from byCycle.model.entities.util import cascade_args
from byCycle.model.data.sqltypes import POINT, LINESTRING

__all__ = ['Node', 'Edge', 'StreetName', 'City', 'State', 'Place']


def base_statements(base_entity_name):
    """Pseudo-statement to import the statements from a "base" entity.

    When this pseudo-statement is added as the first statement in an
    ``Entity`` class definition, it effectively copies the statements from the
    "base" ``Entity`` identified by ``base_entity_name`` to the "child"
    ``Entity`` that executes the statement.

    """
    entity = globals()[base_entity_name]
    class_locals = sys._getframe(1).f_locals
    statements = class_locals[STATEMENTS] = getattr(entity, STATEMENTS)[:]


class Node(Entity):
    has_field('geom', POINT(4326))
    has_many('edges_f', of_kind='Edge', inverse='node_f')
    has_many('edges_t', of_kind='Edge', inverse='node_t')

    @property
    def edges(self):
        return list(self.edges_f) + list(self.edges_t)


class Edge(Entity):
    has_field('addr_f_l', Integer)
    has_field('addr_f_r', Integer)
    has_field('addr_t_l', Integer)
    has_field('addr_t_r', Integer)
    has_field('even_side', CHAR(1)),
    has_field('one_way', Integer)
    has_field('permanent_id', Integer)
    has_field('geom', LINESTRING(4326))
    belongs_to('node_f', of_kind='Node', **cascade_args)
    belongs_to('node_t', of_kind='Node', **cascade_args)
    belongs_to('street_name', of_kind='StreetName', **cascade_args)
    belongs_to('place_l', of_kind='Place', **cascade_args)
    belongs_to('place_r', of_kind='Place', **cascade_args)

    def to_feet(self):
        return self.to_miles() * 5280.0

    def to_miles(self):
        return gis.getLengthOfLineString([self.geom.pointN(n) for n in
                                          range(self.geom.numPoints())])

    def to_kilometers(self):
        return self.to_miles() * 1.609344

    def to_meters(self):
        return self.to_kilometers() / 1000.0

    def getSideNumberIsOn(self, num):
        """Determine which side of the edge, "l" or "r", ``num`` is on."""
        # Determine odd side of edge, l or r, for convenience
        odd_side = ('l', 'r')[self.even_side == 'l']
        # Is ``num`` on the even or odd side of this edge?
        # FIXME: What if there's no address range on the side ``num`` is on?
        #        Right now, we return the odd side by default
        return (odd_side, self.even_side)[int(num) % 2 == 0]

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
            self._length = self.geom.length()
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

        c = self.c

        # Function to get interpolated point
        f = func.line_interpolate_point(c.geom, location)
        # Function to get WKB version of lat/long point
        f = func.asbinary(f)

        # Query DB and get WKB POINT
        select_ = select([f.label('wkb_point')], c.id == self.id)
        result = select_.execute()
        wkb_point = result.fetchone().wkb_point

        point = geometry.Geometry.fromWKB(wkb_point)
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
        num_points = self.geom.numPoints()
        points = [self.geom.pointN(i) for i in range(num_points)]
        N = int(num_points * location) or 1
        if N == num_points:
            N -= 1
        edge_f_points = points[:N] + [point]
        edge_t_points = [point] + points[N:]
        srs = self.geom.srs
        edge_f_geom = geometry.LineString(points=edge_f_points, srs=srs)
        edge_t_geom = geometry.LineString(points=edge_t_points, srs=srs)

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
        geom = self.geom
        shared_node = RegionNode(id=node_id, geom=geom.pointN(N))
        edge_f.node_f = RegionNode(id=self.node_f_id, geom=geom.startPoint())
        edge_f.node_t = shared_node
        edge_t.node_f = shared_node
        edge_t.node_t = RegionNode(id=self.node_t_id, geom=geom.endPoint())

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

    def to_builtin(self):
        return super(Edge, self).to_builtin()


class StreetName(Entity):
    has_field('prefix', String(2))
    has_field('name', String)
    has_field('sttype', String(4))
    has_field('suffix', String(2))

    def __str__(self):
        attrs = (
            (self.prefix or '').upper(),
            self._name_for_str(),
            (self.sttype or '').title(),
            (self.suffix or '').upper()
        )
        return joinAttrs(attrs)

    def to_builtin(self):
        return {
            'prefix': (self.prefix or '').upper(),
            'name': self._name_for_str(),
            'sttype': (self.sttype or '').title(),
            'suffix': (self.suffix or '').upper()
        }

    def _name_for_str(self):
        """Return lower case name if name starts with int, else title case."""
        name = self.name
        no_name = '[No Street Name]'
        try:
            int(name[0])
        except ValueError:
            name = name.title()
        except TypeError:
            # Street name not set (`None`)
            if name is None:
                name = name = no_name
            else:
                name = str(name)
        except IndexError:
            # Empty street name ('')
            name = no_name
        else:
            name = name.lower()
        return name

    def __nonzero__(self):
        """A `StreetName` must have at least a `name`."""
        return bool(self.name)

    def __eq__(self, other):
        self_attrs = (self.prefix, self.name, self.sttype, self.suffix)
        try:
            other_attrs = (other.prefix, other.name, other.sttype, other.suffix)
        except AttributeError:
            return False
        return (self_attrs == other_attrs)

    def almostEqual(self, other):
        self_attrs = (self.name, self.sttype)
        try:
            other_attrs = (other.name, other.sttype)
        except AttributeError:
            return False
        return (self_attrs == other_attrs)


class City(Entity):
    has_field('city', String)

    def __str__(self):
        if self.city:
            return self.city.title()
        else:
            return '[No City]'

    def to_builtin(self):
        return {
            'id': self.id,
            'city': str(self)
        }

    def __nonzero__(self):
        return bool(self.city)


class State(Entity):
    has_field('code', CHAR(2))  # Two-letter state code
    has_field('state', String)

    def __str__(self):
        if self.code:
            return self.code.upper()
        else:
            return '[No State]'

    def to_builtin(self):
        return {
            'id': self.id,
            'code': str(self),
            'state': str(self.state or '[No State]').title()
        }

    def __nonzero__(self):
        return bool(self.code or self.state)



class Place(Entity):
    has_field('zip_code', Integer)
    belongs_to('city', of_kind='City', **cascade_args)
    belongs_to('state', of_kind='State', **cascade_args)

    def _get_city_name(self):
        return (self.city.city if self.city is not None else None)
    def _set_city_name(self, name):
        if self.city is None:
            self.city = City()
        self.city.city = name
    city_name = property(_get_city_name, _set_city_name)

    def _get_state_code(self):
        return (self.state.code if self.state is not None else None)
    def _set_state_code(self, code):
        if self.state is None:
            self.state = State()
        self.state.code = code
    state_code = property(_get_state_code, _set_state_code)

    def _get_state_name(self):
        return (self.state.state if self.state is not None else None)
    def _set_state_name(self, name):
        if self.state is None:
            self.state = State()
        self.state.state = name
    state_name = property(_get_state_name, _set_state_name)

    def __str__(self):
        city_state = joinAttrs([self.city, self.state], ', ')
        return joinAttrs([city_state, str(self.zip_code or '')])

    def to_builtin(self):
        return {
            'city': (self.city.to_builtin() if self.city is not None else None),
            'state': (self.state.to_builtin() if self.state is not None else None),
            'zip_code': str(self.zip_code or None)
        }

    def __nonzero__(self):
        return bool(self.city or self.state or (self.zip_code is not None))
