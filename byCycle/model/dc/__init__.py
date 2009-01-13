###############################################################################
# $Id: __init__.py 918 2007-05-25 18:48:44Z bycycle $
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
from byCycle.model.dc.data import SRID, slug

from dijkstar import infinity

__all__ = ['Edge', 'Node', 'StreetName', 'City', 'State', 'Place']


options_defaults['shortnames'] = True
options_defaults['inheritance'] = None
options_defaults['table_options']['schema'] = slug

metadata = db.metadata_factory(slug)


class Edge(base.Edge):
    base_statements('Edge')
    has_field('geom', LINESTRING(SRID))
    has_field('code', Integer)
    has_field('bikemode', String)

    @classmethod
    def _adjustRowForMatrix(cls, row):
        geom = row.geom
        length = gis.getLengthOfLineString(
            [geom.pointN(n) for n in range(geom.numPoints())])
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
