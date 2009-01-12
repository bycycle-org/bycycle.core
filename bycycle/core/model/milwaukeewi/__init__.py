###############################################################################
# $Id$
# Created 2005-11-07
#
# Milwaukee, WI, region.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from sqlalchemy.types import Integer, String, CHAR, Integer

from byCycle.util import gis
from byCycle.model import db
from byCycle.model.entities import base
from byCycle.model.entities.util import encodeFloat
from byCycle.model.entities.base import base_statements
from byCycle.model.data.sqltypes import POINT, LINESTRING
from byCycle.model.milwaukeewi.data import SRID, slug


__all__ = ['Edge', 'Node', 'StreetName', 'City', 'State', 'Place']


class Edge(base.Edge):
    base_statements('Edge')
    has_field('geom', LINESTRING(SRID))
    has_field('code', CHAR(3))
    has_field('bikemode', CHAR(1))  # enum(t, r, l, p)
    has_field('lanes', Integer)
    has_field('adt', Integer)
    has_field('spd', Integer)

    @classmethod
    def _adjustRowForMatrix(cls, row):
        length = row.geom.length
        return {'length': encodeFloat(length)}


class Node(base.Node):
    base_statements('Node')
    has_field('geom', POINT(SRID))

    @property
    def edges(self):
        return super(Node, self).edges


class StreetName(base.StreetName):
    base_statements('StreetName')


class City(base.City):
    base_statements('City')


class State(base.State):
    base_statements('State')


class Place(base.Place):
    base_statements('Place')
