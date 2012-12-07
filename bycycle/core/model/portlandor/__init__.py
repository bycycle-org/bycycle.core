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
from sqlalchemy.orm import relationship
from sqlalchemy.types import CHAR, Integer, Numeric, Float

from bycycle.core.model import db
from bycycle.core.model.entities import base
from bycycle.core.model.entities.util import encodeFloat
from bycycle.core.model.data.sqltypes import POINT, LINESTRING
from bycycle.core.model.portlandor.data import SRID, slug


table_args = dict(schema='portlandor')


class Node(base.Base, base.Node):

    __table_args__ = table_args

    permanent_id = Column(Integer)
    geom = Column(POINT(SRID))


class Edge(base.Base, base.Edge):

    __table_args__ = table_args

    geom = Column(LINESTRING(SRID))
    permanent_id = Column(Numeric(11, 2))
    code = Column(Integer)
    bikemode = Column(CHAR(1))  # enum('','p','t','b','l','m','h','c','x')
    up_frac = Column(Float)
    abs_slope = Column(Float)
    cpd = Column(Integer)
    sscode = Column(Integer)

    node_f_id = Column(Integer, ForeignKey(Node.id))
    node_t_id = Column(Integer, ForeignKey(Node.id))

    node_f = relationship(Node, primaryjoin=(node_f_id == Node.id), cascade='all')
    node_t = relationship(Node, primaryjoin=(node_t_id == Node.id), cascade='all')

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
            'bikemode': row.bikemode.encode('ascii'),
        }
        return adjustments


Node.edges_f = relationship(Edge, primaryjoin=(Edge.node_f_id == Node.id))
Node.edges_t = relationship(Edge, primaryjoin=(Edge.node_t_id == Node.id))
