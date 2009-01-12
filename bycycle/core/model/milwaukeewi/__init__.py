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
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Integer, CHAR

from bycycle.core.model import db
from bycycle.core.model.entities import base
from bycycle.core.model.entities.util import encodeFloat
from bycycle.core.model.data.sqltypes import POINT, LINESTRING
from bycycle.core.model.milwaukeewi.data import SRID, slug

from dijkstar import infinity


__all__ = ['MilwaukeeWINode', 'MilwaukeeWIEdge']


table_args = dict(schema='milwaukeewi')


class MilwaukeeWINode(base.Node):
    __tablename__ = 'nodes'
    __table_args__ = table_args
    __mapper_args__ = dict(polymorphic_identity='milwaukeewi_node')

    id = Column(Integer, ForeignKey('public.nodes.id'), primary_key=True)
    geom = Column(POINT(SRID))

    @property
    def edges(self):
        return super(Node, self).edges

Node = MilwaukeeWINode


class MilwaukeeWIEdge(base.Edge):
    __tablename__ = 'edges'
    __table_args__ = table_args
    __mapper_args__ = dict(polymorphic_identity='milwaukeewi_edge')

    id = Column('id', Integer, ForeignKey('public.edges.id'), primary_key=True)
    geom = Column(LINESTRING(SRID))
    code = Column(CHAR(3))
    bikemode = Column(CHAR(1))  # enum(t, r, l, p)
    lanes = Column(Integer)
    adt = Column(Integer)
    spd = Column(Integer)

    @classmethod
    def _adjustRowForMatrix(cls, row):
        return {'length': encodeFloat(row.geom.length)}

Edge = MilwaukeeWIEdge
