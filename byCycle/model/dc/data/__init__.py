###############################################################################
# $Id: __init__.py 497 2007-02-18 02:04:51Z bycycle $
# Created 2009-01-12
#
# Washington, DC, data
#
# Copyright (C) 2009 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
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


__all__ = [
    'title', 'slug', 'SRID', 'units', 'earth_circumference',
    'block_length', 'jog_length', 'cities_atof', 'states', 'one_ways',
    'bikemodes', 'edge_attrs', 'Raw'
]


title = 'Washington, DC, metro region'
slug = 'dc'
SRID = 4326
units = 'dd'
earth_circumference = 360
block_length = 0.00071187004976519237  # ~260ft
jog_length = block_length / 2.0
edge_attrs = []

# States to insert into states table in insert_states()
states = {'': '', 'va': 'virginia'}

# dbf value => database value
one_ways = {0: 0, 1: 1, 2: 2, None: 3}

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
    has_field('fnode_', Integer, key='node_f_id')
    has_field('tnode_', Integer, key='node_t_id')

    has_field('l_add_f', Integer, key='addr_f_l')
    has_field('l_add_t', Integer, key='addr_t_l')
    has_field('r_add_f', Integer, key='addr_f_r')
    has_field('r_add_t', Integer, key='addr_t_r')

    has_field('fid_1', Integer, key='permanent_id')
    has_field('class', Integer, key='code')
    has_field('oneway_fin', Integer, key='one_way')
    has_field('bike_fac', String, key='bikemode')

    # To street names table
    has_field('prefix', String(2), key='prefix')
    has_field('name', String(30), key='name')
    has_field('type', String(4), key='sttype')
    has_field('suffix', String(2), key='suffix')

    # To cities table
    has_field('city_l', String(4), key='city_l')
    has_field('city_r', String(4), key='city_r')

    # To places table
    has_field('zip_l', Integer, key='zip_code_l')
    has_field('zip_r', Integer, key='zip_code_r')

