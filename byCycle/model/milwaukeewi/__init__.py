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
from sqlalchemy import MetaData

from elixir import Entity, options_defaults, has_field
from elixir import Integer, String, CHAR, Integer

from byCycle.util import gis
from byCycle.model import db
from byCycle.model.entities import base
from byCycle.model.entities.util import encodeFloat
from byCycle.model.entities.base import base_statements
from byCycle.model.data.sqltypes import POINT, LINESTRING
from byCycle.model.milwaukeewi.data import SRID, slug

__all__ = ['Edge', 'Node', 'StreetName', 'City', 'State', 'Place']


options_defaults['shortnames'] = True
options_defaults['inheritance'] = None
options_defaults['table_options']['schema'] = slug

metadata = db.metadata_factory(slug)


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
        geom = row.geom
        length = gis.getLengthOfLineString([geom.pointN(n) for n in
                                            range(geom.numPoints())])
        
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
