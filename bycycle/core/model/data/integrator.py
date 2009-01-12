###############################################################################
# $Id: shp2pgsql.py 187 2006-08-16 01:26:11Z bycycle $
# Created 2007-05-08
#
# Base regional data integrator.
#
# Copyright (C) 2006-2008 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Provides a base class for integrating regional data.

Notes:

    - Expects `psql` and `shp2pgsql` to be on your ${PATH}

    - Expects a module at byCycle/model/<region key> that contains the
      region's entity classes

    - Expects a module at byCycle/model/<region key>/data that contains the
      region's "raw" entity class

    - The data module should also contain:
      - ``cities_atof`` that maps abbreviated city names to full city names
      - ``states`` that maps two-letter state codes to full state names
      - ``one_ways`` that maps the region's one way attributes to...
        - 0 for no travel in either direction
        - 1 for travel in the from => to direction
        - 2 for travel in the to => from direction
        - 3 for travel in either direction
      - ``bikemodes`` that maps the region's bike mode attribute to...
        - whatever format you want in the DB
      - ``edge_attrs``, which is a list of the edge attributes that are used
        for route finding

    - Expects all data to be lower case

"""
import os, sys

import psycopg2

import sqlalchemy
from sqlalchemy import func, select, text, and_, or_

from bycycle.core.util import meter
from bycycle.core import model_path
from bycycle.core.model import db
from bycycle.core.model.entities import base, public
from bycycle.core.model.sttypes import street_types_ftoa


db.connectMetadata()


class Integrator(object):

    user = os.environ['USER']
    db_name = '%s_beta' % user
    base_data_path = os.path.join('/home/%s' % user, 'byCycleData')
    overall_timer = meter.Timer(start_now=True)
    timer = meter.Timer(start_now=False)

    def __init__(self, region_key, source, layer, no_prompt, **opts):
        self.region_key = region_key
        self.raw_table = self.region_data_module.Raw.__table__
        self.source = source
        self.layer = layer
        self.no_prompt = no_prompt

    def run(self, start=0, end=None, no_prompt=False, only=None):
        if only is not None:
            start = only
            end = only
            no_prompt = True
        do_prompt = not no_prompt
        print
        for i, action in enumerate(self.actions):
            msg = action.__doc__
            if i < start or i > end:
                print '%s: Skipping "%s"' % (i, msg)
            else:
                if do_prompt:
                    # Ask user, "Do you want do this action?"
                    self.overall_timer.pause()
                    response = self.prompt(msg=msg, prefix=i)
                    self.overall_timer.unpause()
                else:
                    print '%s: %s..' % (i, msg)
                if no_prompt or response:
                    # Yes, do this action
                    self.timer.start()
                    try:
                        action(self)
                    except Exception, e:
                        print ('\n*** Errors encountered in action %s.' % i)
                        raise
                    print 'Took %s' % self.getTimeWithUnits(self.timer.stop())
                else:
                    # No, don't do this action
                    print 'Skipped'
            print
        overall_time = self.overall_timer.stop()
        print 'Total time: %s' % self.getTimeWithUnits(overall_time)

    # Actions the user may or may not want to take ----------------------------

    def shp2sql(self):
        """Convert shapefile to raw SQL and save to file."""
        # Path to regional shapefiles (i.e., to a particular datasource for
        # the region)
        data_path = os.path.join(self.base_data_path, self.region_key,
                                 self.source)

        # Path to layer within data source
        layer_path = os.path.join(data_path, self.layer)

        # Command to convert shapefile to raw SQL
        # Ex: shp2pgsql -c -i -I -s 2913 str06oct raw.portlandor > \
        #               /path/portlandor_str06oct_raw.sql
        shp2sql_cmd = 'shp2pgsql -c -i -I -s %s %s %s.%s > %s'
                                 # % (SRID, layer, schema, SQL file)

        shp2sql_cmd = shp2sql_cmd % (self.region_data_module.SRID,
                                     layer_path, self.raw_table.schema,
                                     self.raw_table.name,
                                     self.get_sql_file_path())
        self.system(shp2sql_cmd)

    def shp2db(self):
        """Drop existing raw table and insert raw SQL into database."""
        # Command to import raw SQL into database
        # Ex: psql --quiet -d ${USER} -f /path/to/portlandor_raw.sql
        sql2db_cmd = 'psql --quiet -d %s -f %s'  # % (database, SQL file)
        sql2db_cmd = sql2db_cmd % (self.db_name, self.get_sql_file_path())
        db.createSchema('raw')   # if it doesn't exist
        db.dropTable(self.raw_table)  # if it exists
        self.system(sql2db_cmd)
        db.vacuum('raw.%s' % self.region_key)

    def create_public_tables(self):
        """Create public tables."""
        for table in db.metadata.sorted_tables:
            if (table.schema or 'public') == 'public':
                table.create(checkfirst=True)

    def delete_region(self):
        """Delete region and any dependent records."""
        try:
            region = public.Region.get_by_slug(self.region_key)
        except sqlalchemy.orm.exc.NoResultFound:
            pass
        except sqlalchemy.exc.ProgrammingError, e:
            if not 'does not exist' in str(e):
                raise
        else:
            db.Session.delete(region)
            db.Session.flush()

    def get_or_create_region(self):
        """Create region."""
        public.Region.__table__.create(checkfirst=True)
        try:
            region = public.Region.get_by_slug(self.region_key)
        except sqlalchemy.orm.exc.NoResultFound, e:
            self.echo('Region %s not found.' % self.region_key)
            region = None
        if region is None:
            self.echo('Creating region %s.' % self.region_key)

            data = self.region_data_module
            region = public.Region(
                title=data.title,
                slug=self.region_key,
                srid=data.SRID,
                units=data.units,
                earth_circumference=data.earth_circumference,
                block_length=data.block_length,
                jog_length=data.jog_length,
                map_type=data.map_type,
            )
            db.Session.flush()

            # Add edge attributes
            self.echo('Adding edge attributes to region.')
            region.edge_attrs = []
            for a in self.region_data_module.edge_attrs:
                region.edge_attrs.append(public.EdgeAttr(name=a))

            db.Session.add(region)
            db.Session.flush()
            db.Session.refresh(region)
        return region

    def drop_schema(self):
        """Drop SCHEMA for region."""
        self.echo('Dropping edge table for region...')
        db.dropTable(self.region_module.Edge.__table__, cascade=True)
        self.echo('Dropping node table for region...')
        db.dropTable(self.region_module.Node.__table__, cascade=True)
        Q = "DELETE FROM %s WHERE type = '%s_%s'"
        args = ('edges', self.region_key, 'edge')
        self.echo(Q % args)
        db.execute(Q % args)
        args = ('nodes', self.region_key, 'node')
        self.echo(Q % args)
        db.execute(Q % args)
        db.commit()
        self.echo('Dropping schema for region...')
        db.dropSchema(self.region_key, cascade=True)

    def create_schema(self):
        """Create database SCHEMA for region including public tables."""
        db.createSchema(self.region_key)
        db.createAllTables()

    def drop_schema_tables(self):
        """Drop all regional tables (not including raw or public)."""
        region = self.get_or_create_region()
        for table in db.metadata.sorted_tables:
            if table.schema == self.region_module.Edge.__table__.schema:
                db.dropTable(table, cascade=True)

    def create_schema_tables(self):
        """Create all regional tables. Ignores existing tables."""
        region = self.get_or_create_region()
        db.createAllTables()
        schema = self.region_module.Edge.__table__.schema
        SRID = self.region_data_module.SRID
        db.addGeometryColumn(
            self.region_module.Edge.__table__.name, SRID, 'LINESTRING',
            schema=schema)
        db.addGeometryColumn(
            self.region_module.Node.__table__.name, SRID,
            'POINT', schema=schema)

    def transfer_street_names(self):
        """Transfer street names from raw table."""
        StreetName = public.StreetName
        region = self.get_or_create_region()
        region_id = region.id
        c = self.region_data_module.Raw.__table__.c
        cols = map(func.lower, (c.prefix, c.name, c.sttype, c.suffix))
        raw_records = self.get_records(cols)
        c = StreetName
        cols = map(func.lower, (c.prefix, c.name, c.sttype, c.suffix))
        existing_records = self.get_records(cols)
        new_records = raw_records.difference(existing_records)
        records = []
        for record in new_records:
            p, n, t, s = record
            t = street_types_ftoa.get(t, t)
            records.append(dict(prefix=p, name=n, sttype=t, suffix=s))
        self.echo('Inserting street names...')
        self.insert_records(StreetName.__table__, records, 'street names')
        self.vacuum_entity(StreetName)

    def transfer_cities(self):
        """Transfer cities from raw table."""
        City = public.City
        cities_atof = self.region_data_module.cities_atof
        c = self.region_data_module.Raw.__table__.c
        raw_records_l = self.get_records([func.lower(c.city_l)])
        raw_records_r = self.get_records([func.lower(c.city_r)])
        raw_records = raw_records_l.union(raw_records_r)
        raw_records = set([(cities_atof[r[0]],) for r in raw_records])
        existing_records = self.get_records([City.city])
        new_records = raw_records.difference(existing_records)
        records = []
        city_names = []
        for r in new_records:
            city_name = r[0]
            city_names.append(city_name)
            records.append(dict(city=city_name))
        self.insert_records(City.__table__, records, 'cities')
        self.vacuum_entity(City)

    def transfer_states(self):
        """Transfer states."""
        State = public.State
        states = self.region_data_module.states
        raw_records = set(states.items())
        existing_records = self.get_records([State.code, State.state])
        new_records = raw_records.difference(existing_records)
        records = []
        codes = []
        for r in new_records:
            code, state = r[0], r[1]
            codes.append(code)
            records.append(dict(code=code, state=state))
        self.insert_records(State.__table__, records, 'states')
        self.vacuum_entity(State)

    def transfer_places(self):
        """Create places."""
        City = public.City
        State = public.State
        Place = public.Place
        cities_atof = self.region_data_module.cities_atof
        states = self.region_data_module.states

        c = self.region_data_module.Raw.__table__.c
        cols = (func.lower(c.city_l), c.zip_code_l)
        raw_records_l = self.get_records(cols)
        cols = (func.lower(c.city_r), c.zip_code_r)
        raw_records_r = self.get_records(cols)
        raw_records = raw_records_l.union(raw_records_r)
        def get_city_state_and_zip(r):
            city, zip_code = r[0], r[1]
            city = cities_atof[city] if city is not None else None
            state = self.get_state_code_for_city(city)
            zip_code = int(zip_code) if zip_code is not None else zip_code
            return city, state, zip_code
        raw_records = set([get_city_state_and_zip(r) for r in raw_records])

        places = db.Session.query(Place).all()
        existing_records = set([(p.city_name, p.state_code, p.zip_code) for p
                                in places])

        records = []
        new_records = raw_records.difference(existing_records)
        city_q = db.Session.query(City)
        state_q = db.Session.query(State)
        for r in new_records:
            city_name, state_code, zc = r[0], r[1], r[2]
            city = city_q.filter_by(city=city_name).one()
            state = state_q.filter_by(code=state_code, state=states[state_code]).one()
            city_id = None if city is None else city.id
            state_id = None if state is None else state.id
            records.append(
                dict(city_id=city_id, state_id=state_id, zip_code=zc))
        self.insert_records(Place.__table__, records, 'places')

        self.vacuum_entity(Place)

    def transfer_nodes(self):
        """Transfer nodes from raw table to node table."""
        Node = self.region_module.Node

        region = self.get_or_create_region()

        self.echo('Getting columns from raw table...')
        c = self.region_data_module.Raw.__table__.c
        raw_records_f = self.get_records(
            [c.node_f_id, func.startPoint(c.geom)], distinct=False)
        raw_records_t = self.get_records(
            [c.node_t_id, func.endPoint(c.geom)], distinct=False)

        base_records, records = [], []
        seen_nodes = set()
        id_query = select([func.nextval('nodes_id_seq')], bind=db.engine)
        type = '%s_node' % self.region_key
        region_id = region.id
        def collect_records(raw_records):
            for r in raw_records:
                id = id_query.scalar()
                permanent_id = r[0]
                if permanent_id in seen_nodes:
                    continue
                seen_nodes.add(permanent_id)
                geom = r[1]
                base_records.append(dict(id=id, type=type, region_id=region_id))
                records.append(
                    dict(id=id, permanent_id=permanent_id, geom=geom))
        collect_records(raw_records_f)
        collect_records(raw_records_t)

        self.echo('Inserting %i records into node table...' % len(seen_nodes))
        self.insert_records(base.Node.__table__, base_records, 'nodes')
        self.insert_records(Node.__table__, records, '%s.nodes' % self.region_key)

        self.vacuum_entity(Node)

    def transfer_edges(self):
        """Transfer edges from raw table."""
        region = self.get_or_create_region()

        Edge = self.region_module.Edge
        Node = self.region_module.Node
        StreetName = public.StreetName
        Place = public.Place
        cities_atof = self.region_data_module.cities_atof
        one_ways = self.region_data_module.one_ways
        bikemodes = self.region_data_module.bikemodes
        edge_attrs = self.region_data_module.edge_attrs

        self.echo('Getting columns from raw table...')
        c = self.region_data_module.Raw.__table__.c
        cols = [
            c.id, c.geom, c.node_f_id, c.node_t_id,
            c.addr_f_l, c.addr_t_l, c.addr_f_r, c.addr_t_r,
            c.zip_code_l, c.zip_code_r,
            c.permanent_id, c.code
        ]
        cols += [c[name] for name in edge_attrs]
        for i, col in enumerate(cols):
            cols[i] = col.label(col.key)
        lower_cols = [
            c.prefix, c.name, c.sttype, c.suffix,
            c.city_l, c.city_r, c.one_way, c.bikemode
        ]
        for i, col in enumerate(lower_cols):
            lower_cols[i] = func.lower(col).label(col.key)
        cols += lower_cols
        raw_records = select(cols).execute()

        self.echo('Getting street names...')
        c = StreetName
        street_names = self.get_records(
            (c.prefix, c.name, c.sttype, c.suffix, c.id))
        street_names = dict(
            [((r[0], r[1], r[2], r[3]), r[4]) for r in street_names])
        street_names[(None, None, None, None)] = None

        self.echo('Getting places...')
        places = db.Session.query(Place).all()
        places = dict(
            [((p.city_name, p.state_code, p.zip_code), p.id) for p in places])
        places[(None, None, None)] = None

        i = 1
        id_query = select([func.nextval('edges_id_seq')], bind=db.engine)
        step = 2500
        num_records = raw_records.rowcount
        base_records, records = [], []
        self.echo('Getting ID and permanent ID of base nodes...')
        slug = self.region_key
        Q = 'SELECT %s.nodes.id, %s.nodes.permanent_id FROM %s.nodes'
        s = text(Q % (slug, slug, slug))
        node_records = db.engine.connect().execute(s)
        self.echo('Mapping base node permanent IDs to their IDs...')
        node_map = dict([(nr.permanent_id, nr.id) for nr in node_records])
        region_id = region.id
        self.echo('Transferring edges...')
        for r in raw_records:
            id = id_query.scalar()
            even_side = self.getEvenSide(
                r.addr_f_l, r.addr_f_r, r.addr_t_l, r.addr_t_r)
            node_f_id = node_map[r.node_f_id]
            node_t_id = node_map[r.node_t_id]
            sttype = street_types_ftoa.get(r.sttype, r.sttype)
            st_name_id = street_names[(r.prefix, r.name, sttype, r.suffix)]
            city_l = cities_atof[r.city_l]
            city_r = cities_atof[r.city_r]
            state_l = self.get_state_code_for_city(city_l)
            state_r = self.get_state_code_for_city(city_r)
            zl = int(r.zip_code_l) if r.zip_code_l is not None else None
            zr = int(r.zip_code_r) if r.zip_code_r is not None else None
            place_l_id = places[(city_l, state_l, zl)]
            place_r_id = places[(city_r, state_r, zr)]
            base_record = dict(
                id=id,
                type='%s_edge' % self.region_key,
                region_id=region_id,
                addr_f_l=r.addr_f_l or None,
                addr_f_r=r.addr_f_r or None,
                addr_t_l=r.addr_t_l or None,
                addr_t_r=r.addr_t_r or None,
                even_side=even_side,
                one_way=one_ways[r.one_way],
                node_f_id=node_f_id,
                node_t_id=node_t_id,
                street_name_id=st_name_id,
                place_l_id=place_l_id,
                place_r_id=place_r_id,
            )
            base_records.append(base_record)
            record = dict(
                id=id,
                geom=r.geom.geometryN(0),
                permanent_id=r.permanent_id,
                bikemode=bikemodes[r.bikemode],
                code=r.code,
            )
            # fields that are specific to a region:
            for attr in edge_attrs:
                record[attr] = r[attr]
            records.append(record)
            if (i % step) == 0:
                self.echo('Inserting %s records into edge table...' % step)
                self.insert_records(base.Edge.__table__, base_records, 'edges')
                self.insert_records(Edge.__table__, records, '%s.edges' % self.region_key)
                self.echo('%i down, %i to go' % (i, num_records - i))
                base_records, records = [], []
            i += 1
        if records:
            self.echo('Inserting remaining records into edge table...')
            self.insert_records(base.Edge.__table__, base_records, 'edges')
            self.insert_records(Edge.__table__, records, '%s.edges' % self.region_key)
            self.vacuum_entity(Edge)

    def vacuum_all_tables(self):
        """Vacuum all tables."""
        db.vacuum()

    def create_matrix(self):
        """Create adjency matrix for region."""
        self.get_or_create_region().createAdjacencyMatrix()

    #-- Utility methods --#
    def system(self, cmd):
        """Run the command specified by ``cmd``."""
        print cmd
        exit_code = os.system(cmd)
        if exit_code:
            sys.exit()

    def wait(self, msg='Continue or skip'):
        if self.no_prompt:
            return False
        self.timer.pause()
        resp = raw_input(msg.strip() + ' ')
        self.timer.unpause()
        return resp

    def prompt(self, msg='', prefix=None, default='no'):
        """Prompt, wait for response, and return response.

        ``msg`` `string`
            The prompt message, in the form of a question.

        ``prefix``
            Something to prefix the prompt with (like a number to indicate
            which action we're on).

        ``default`` `string` `bool`
            The default response for this prompt (when the user just presses
            Enter). Can be 'n', 'no', or anything that will evaluate as False
            to set the default response to 'no'. Otherwise the default
            response will be 'yes'.

        Return `bool`
            True indicates a positive (Go ahead) response.
            False indicates a negative (Don't do it!) response.

        """
        msg = msg.strip() or 'Are you sure'
        # Prefix prompt with prefix if prefix supplied
        if prefix is None:
            p = ''
        else:
            p = '%s: ' % prefix
        # Determine if yes or no is the default response
        if not default or str(default).lower() in ('n', 'no'):
            choices = '[y/N]'
            default_is_yes = False
        else:
            choices = '[Y/n]'
            default_is_yes = True
        default_is_no = not default_is_yes
        # Print prompt and wait for response
        resp = raw_input('%s%s? %s '% (p, msg.rstrip('.'), choices)).strip().lower()
        # Interpret and return response
        if not resp:
            if default_is_yes:
                return True
            elif default_is_no:
                return False
        else:
            if resp[0] == 'y':
                return True
            elif resp[0] in ('q', 'x') or resp == 'exit':
                print '\n***Aborted at action %s.***' % prefix
                sys.exit(0)
            else:
                return False

    def getEvenSide(self, addr_f_l, addr_f_r, addr_t_l, addr_t_r):
        """Figure out which side of the edge even addresses are on."""
        if ((addr_f_l and addr_f_l % 2 == 0) or
            (addr_t_l and addr_t_l % 2 == 0)):
            # Left?
            even_side = 'l'
        elif ((addr_f_r and addr_f_r % 2 == 0) or
              (addr_t_r and addr_t_r % 2 == 0)):
            # Right?
            even_side = 'r'
        else:
            # Couldn't tell.
            even_side = None
        return even_side

    def getTimeWithUnits(self, seconds):
        """Convert ``seconds`` to minutes if >= 60. Return time with units."""
        if seconds >= 60:
            time = seconds / 60.0
            units = 'minute'
        else:
            time = seconds
            units = 'second'
        if time != 1.0:
            units +=  's'
        return '%.2f %s' % (time, units)

    def any_not_none(self, sequence):
        """Return ``True`` if any item in ``sequence`` is not ``None``."""
        return any([e is not None for e in sequence])

    def get_records(self, cols, distinct=True):
        """Get distinct records.

        ``cols``
            The list of cols to select

        return
            A ``set`` of ``tuple``s of column values, in the same order as
            ``cols``

        """
        result = select(cols, distinct=distinct).execute()
        records = set([tuple([v for v in row]) for row in result])
        result.close()
        return records

    def insert_records(self, table, records, kind='records'):
        """Insert ``records`` into ``table``.

        ``table``
            SQLAlchemy table object

        ``records``
            A ``list`` of ``dict``s representing the records

        """
        if records:
            table.insert().execute(records)
            self.echo('%i new %s added' % (len(records), kind))
        else:
            self.echo('No new %s added' % kind)

    def get_sql_file_path(self):
        """Get output file for SQL imported from shapefile.

        The output file will be created in the directory this script is in. It
        will include the region's schema (AKA slug), datasource, and layer::

            /path/to/here/<slug>_<source>_<layer>_raw.sql

        """
        sql_file_path = getattr(self, '_sql_file_path', None)
        if sql_file_path is None:
            # Name of the SQL file
            sql_file = '%s_%s_raw.sql' % (self.source.replace('/', '_'),
                                          self.layer)
            # Full path (including file name)
            sql_file_path = os.path.join(model_path, self.region_key, 'data',
                                         sql_file)
            self._sql_file_path = sql_file_path
        return sql_file_path

    def vacuum_entity(self, entity):
        args = (entity.__table__.schema or 'public', entity.__table__.name)
        self.echo('Vacuuming %s.%s...' % args)
        db.vacuum('%s.%s' % args)

    def echo(self, *args):
        for msg in args:
            print '    - %s' % msg

    #-- Default actions and the order in which they will be run --#
    actions = [
        shp2sql,
        shp2db,
        create_public_tables,
        delete_region,
        get_or_create_region,
        drop_schema,
        create_schema,
        drop_schema_tables,
        create_schema_tables,
        transfer_street_names,
        transfer_cities,
        transfer_states,
        transfer_places,
        transfer_nodes,
        transfer_edges,
        vacuum_all_tables,
        create_matrix,
    ]
