###############################################################################
# $Id$
# Created 2005-11-07
#
# Portland, OR, region.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from sqlalchemy import MetaData

from elixir import Entity, options_defaults, has_field
from elixir import Unicode, Integer, String, CHAR, Integer, Numeric, Float

from byCycle.model import db
from byCycle.model.entities import base
from byCycle.model.entities.base import base_statements
from byCycle.model.entities.util import encodeFloat
from byCycle.model.data.sqltypes import POINT, LINESTRING
from byCycle.model.portlandor.data import SRID, slug

from dijkstar import infinity

__all__ = ['Edge', 'Node', 'StreetName', 'City', 'State', 'Place']


options_defaults['shortnames'] = True
options_defaults['inheritance'] = None
options_defaults['table_options']['schema'] = slug

metadata = db.metadata_factory(slug)


class Edge(base.Edge):
    base_statements('Edge')
    has_field('geom', LINESTRING(SRID))
    has_field('permanent_id', Numeric(11, 2))
    has_field('code', Integer)
    has_field('bikemode', CHAR(1))  # enum('','p','t','b','l','m','h','c','x')
    has_field('up_frac', Float)
    has_field('abs_slope', Float)
    has_field('cpd', Integer)
    has_field('sscode', Integer)

    def to_feet(self):
        return self.geom.length()

    def to_miles(self):
        return self.to_feet() / 5280.0

    def to_kilometers(self):
        return self.to_miles() * 1.609344

    def to_meters(self):
        return self.to_kilometers() * 1000.0

    @classmethod
    def _adjustRowForMatrix(cls, row):
        adjustments = {
            'length': encodeFloat(row.geom.length() / 5280.0),
            'abs_slope': encodeFloat(row.abs_slope),
            'up_frac': encodeFloat(row.up_frac),
        }
        return adjustments


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
