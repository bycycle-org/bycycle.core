###############################################################################
# $Id: __init__.py 497 2007-02-18 02:04:51Z bycycle $
# Created 2005-11-07
#
# Portland, OR, data
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""This package contains everything to do with this region's data and DB."""
from sqlalchemy import Column
from sqlalchemy.types import Integer, String, Integer, Float, Numeric

from bycycle.core.model import db
from bycycle.core.model.entities import Base
from bycycle.core.model.data.sqltypes import MULTILINESTRING

from cities import cities_atof

__all__ = [
    'title', 'slug', 'SRID', 'units', 'earth_circumference', 'block_length',
    'jog_length', 'cities_atof', 'states', 'one_ways', 'bikemodes',
    'edge_attrs', 'Raw']


title = 'Portland, OR, metro region'
slug = 'portlandor'
SRID = 2913
units = 'feet'
earth_circumference = 131484672
block_length = 260
jog_length = block_length / 2
edge_attrs = ['up_frac', 'abs_slope', 'cpd', 'sscode']
map_type = 'openlayers'

# States to insert into states table in insert_states()
states = {'or': 'oregon', 'wa': 'washington'}

# dbf value => database value
one_ways = {'n': 0, 'f': 1, 't': 2, '':  3, None: 3}

# dbf value => database value
bikemodes = {
    'mu': 't',
    'mm': 'p',
    'bl': 'b',
    'lt': 'l',
    'mt': 'm',
    'ht': 'h',
    'ca': 'c',
    'pm': 'x',
    'up': 'u',
    'pb': 'n',
    'xx': 'n',
    None: None,
}


class Raw(Base):
    __tablename__ = slug
    __table_args__ = dict(schema='raw')

    gid = Column(Integer, primary_key=True, key='id')

    # To edge table (core)
    the_geom = Column(MULTILINESTRING(SRID), key='geom')
    n0 = Column(Integer, key='node_f_id')
    n1 = Column(Integer, key='node_t_id')
    leftadd1 = Column(Integer, key='addr_f_l')
    leftadd2 = Column(Integer, key='addr_t_l')
    rgtadd1 = Column(Integer, key='addr_f_r')
    rgtadd2 = Column(Integer, key='addr_t_r')
    localid = Column(Numeric(11, 2), key='permanent_id')
    type = Column(Integer, key='code')
    one_way = Column(String(2))
    bikemode = Column(String(2))

    # To street names table
    fdpre = Column(String(2), key='prefix')
    fname = Column(String(30), key='name')
    ftype = Column(String(4), key='sttype')
    fdsuf = Column(String(2), key='suffix')

    # To cities table
    lcity = Column(String(4), key='city_l')
    rcity = Column(String(4), key='city_r')

    # To places table
    lzip = Column(Integer, key='zip_code_l')
    rzip = Column(Integer, key='zip_code_r')

    # To edge table (supplemental)
    upfrc = Column(Float, key='up_frac')
    abslp = Column(Float, key='abs_slope')
    sscode = Column(Integer)
    cpd = Column(Integer)
