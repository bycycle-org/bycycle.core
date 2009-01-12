###############################################################################
# $Id$
# Created 2005-11-07
#
# Portland, OR, region.
#
# Copyright (C) 2006-2008 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Unicode, Integer, String, CHAR, Integer, Numeric, Float

from bycycle.core.model import db
from bycycle.core.model.entities import base
from bycycle.core.model.entities.util import encodeFloat
from bycycle.core.model.data.sqltypes import POINT, LINESTRING
from bycycle.core.model.portlandor.data import SRID, slug

from dijkstar import infinity


__all__ = ['PortlandORNode', 'PortlandOREdge']


table_args = dict(schema='portlandor')


class PortlandORNode(base.Node):
    __tablename__ = 'nodes'
    __table_args__ = table_args
    __mapper_args__ = dict(polymorphic_identity='portlandor_node')

    id = Column(Integer, ForeignKey('public.nodes.id'), primary_key=True)
    permanent_id = Column(Integer)
    geom = Column(POINT(SRID))

    @property
    def edges(self):
        return super(Node, self).edges

Node = PortlandORNode


class PortlandOREdge(base.Edge):
    __tablename__ = 'edges'
    __table_args__ = table_args
    __mapper_args__ = dict(polymorphic_identity='portlandor_edge')

    id = Column('id', Integer, ForeignKey('public.edges.id'), primary_key=True)
    geom = Column(LINESTRING(SRID))
    permanent_id = Column(Numeric(11, 2))
    code = Column(Integer)
    bikemode = Column(CHAR(1))  # enum('','p','t','b','l','m','h','c','x')
    up_frac = Column(Float)
    abs_slope = Column(Float)
    cpd = Column(Integer)
    sscode = Column(Integer)

    def to_feet(self):
        return self.geom.length

    def to_miles(self):
        return self.to_feet() / 5280.0

    def to_kilometers(self):
        return self.to_miles() * 1.609344

    def to_meters(self):
        return self.to_kilometers() * 1000.0

    @classmethod
    def _adjustRowForMatrix(cls, row):
        adjustments = {
            'length': encodeFloat(row.geom.length / 5280.0),
            'abs_slope': encodeFloat(row.abs_slope),
            'up_frac': encodeFloat(row.up_frac),
        }
        return adjustments

Edge = PortlandOREdge
