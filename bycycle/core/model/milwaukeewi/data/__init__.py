###############################################################################
# $Id: __init__.py 497 2007-02-18 02:04:51Z bycycle $
# Created 2005-11-07
#
# Milwaukee, WI, data
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

__all__ = ['title', 'slug', 'SRID', 'units', 'earth_circumference',
           'block_length', 'jog_length', 'cities_atof', 'states', 'one_ways',
           'bikemodes', 'edge_attrs', 'Raw']


title = 'Milwaukee, WI, metro region'
slug = 'milwaukeewi'
SRID = 4326
units = 'dd'
earth_circumference = 360
block_length = 0.00071187004976519237  # ~260ft
jog_length = block_length / 2.0
edge_attrs = ['lanes', 'adt', 'spd']

cities = (
    'Bayside',
    'Brown Deer',
    'Cudahy',
    'Fox Point',
    'Franklin',
    'Glendale',
    'Greendale',
    'Greenfield',
    'Hales Corners',
    'Milwaukee',
    'Oak Creek',
    'River Hills',
    'Saint Francis',
    'Shorewood',
    'South Milwaukee',
    'Wauwatosa',
    'West Allis',
    'West Milwaukee',
    'Whitefish Bay',
)
cities_atof = dict([(c.lower(), c.lower()) for c in cities])
cities_atof[None] = None

# States to insert into states table in insert_states()
states = {'wi': 'wisconsin'}

# dbf value => database value
one_ways = {'0': 0, '1': 1, '2': 2, '3':  3, '': 3, None: 3}

# dbf value => database value
bikemodes = {
    'bike trail': 't',
    'bike route': 'r',
    'bike lane': 'l',
    'preferred street': 'p',
    None: None,
}

class Raw(Base):
    __tablename__ = slug
    __table_args__ = dict(schema='raw')

    gid = Column(Integer, primary_key=True, key='id')

    # TODO: Convert to SA declarative
    ## To edge table (core)
    #has_field('the_geom', MULTILINESTRING(SRID), key='geom')
    #has_field('fnode', Integer, key='node_f_id')
    #has_field('tnode', Integer, key='node_t_id')
    #has_field('fraddl', Integer, key='addr_f_l')
    #has_field('toaddl', Integer, key='addr_t_l')
    #has_field('fraddr', Integer, key='addr_f_r')
    #has_field('toaddr', Integer, key='addr_t_r')
    #has_field('tlid', Float, key='permanent_id')
    #has_field('cfcc', Integer, key='code')
    #has_field('one_way', String(2))
    #has_field('bike_facil', String(2), key='bikemode')

    ## To street names table
    #has_field('fedirp', String(2), key='prefix')
    #has_field('fename', String(30), key='name')
    #has_field('fetype', String(4), key='sttype')
    #has_field('fedirs', String(2), key='suffix')

    ## To cities table
    #has_field('cityl', String(4), key='city_l')
    #has_field('cityr', String(4), key='city_r')

    ## To places table
    #has_field('zipl', Integer, key='zip_code_l')
    #has_field('zipr', Integer, key='zip_code_r')

    ## To edge table (supplemental)
    #has_field('lanes', Integer)
    #has_field('adt', Integer)
    #has_field('spd', Integer)
