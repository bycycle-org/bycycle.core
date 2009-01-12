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
from elixir import Entity, using_options, using_table_options
from elixir import has_field
from elixir import Integer, String, Integer, Float, Numeric

from byCycle.model import db
from byCycle.model.data.sqltypes import MULTILINESTRING

from cities import cities_atof

__all__ = ['title', 'slug', 'SRID', 'units', 'earth_circumference',
           'block_length', 'jog_length', 'cities_atof', 'states', 'one_ways',
           'bikemodes', 'edge_attrs', 'Raw']


title = 'Portland, OR, metro region'
slug = 'portlandor'
SRID = 2913
units = 'feet'
earth_circumference = 131484672
block_length = 260
jog_length = block_length / 2
edge_attrs = ['up_frac', 'abs_slope', 'cpd', 'sscode']

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

metadata = db.metadata_factory(slug)


class Raw(Entity):
    using_options(tablename=slug)
    using_table_options(schema='raw')

    has_field('gid', Integer, primary_key=True, key='id')

    # To edge table (core)
    has_field('the_geom', MULTILINESTRING(SRID), key='geom')
    has_field('n0', Integer, key='node_f_id')
    has_field('n1', Integer, key='node_t_id')
    has_field('leftadd1', Integer, key='addr_f_l')
    has_field('leftadd2', Integer, key='addr_t_l')
    has_field('rgtadd1', Integer, key='addr_f_r')
    has_field('rgtadd2', Integer, key='addr_t_r')
    has_field('localid', Numeric(11, 2), key='permanent_id')
    has_field('type', Integer, key='code')
    has_field('one_way', String(2))
    has_field('bikemode', String(2))

    # To street names table
    has_field('fdpre', String(2), key='prefix')
    has_field('fname', String(30), key='name')
    has_field('ftype', String(4), key='sttype')
    has_field('fdsuf', String(2), key='suffix')

    # To cities table
    has_field('lcity', String(4), key='city_l')
    has_field('rcity', String(4), key='city_r')

    # To places table
    has_field('zipcolef', Integer, key='zip_code_l')
    has_field('zipcorgt', Integer, key='zip_code_r')

    # To edge table (supplemental)
    has_field('upfrc', Float, key='up_frac')
    has_field('abslp', Float, key='abs_slope')
    has_field('sscode', Integer)
    has_field('cpd', Integer)
