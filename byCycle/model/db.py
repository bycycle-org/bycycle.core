################################################################################
# $Id$
# Created 2005-11-07.
#
# Database Connection Handler.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
"""Database connection initialization and handling.

Provides the ``DB`` class, which connects to the database and contains various
generic (i.e., not region-specific) database functions.

"""
from __future__ import with_statement

import os

import psycopg2
import sqlalchemy
from sqlalchemy import MetaData, orm, create_engine

from byCycle import model_path


user = os.environ['USER']
metadata = MetaData()

def init(**connection_args):
    global engine, connection, cursor, Session
    engine = create_engine(getConnectionUri(**connection_args))
    connection = engine.raw_connection()
    cursor = connection.cursor()
    _Session = orm.sessionmaker(autoflush=True, autocommit=True, bind=engine)
    Session = orm.scoped_session(_Session)

def getConnectionUri(db_type='postgres', user=user, password=None,
                     host='', database=user):
    """Get database connection URI (DSN)."""
    if password is None:
        pw_path = os.path.join(model_path, '.pw')
        with file(pw_path) as pw_file:
            password = pw_file.read().strip()
    dburi = '%s://%s:%s@%s/%s' % (db_type, user, password, host, '%s_beta' % database)
    return dburi

def connectMetadata(md=None):
    """Connect metadata to ``engine``. Use ``md`` if specified."""
    (md or metadata).bind = engine

def dropAllTables(md=None):
    md = md or metadata
    md.drop_all()

def createAllTables(md=None):
    md = md or metadata
    md.create_all()

def clearSession():
    del session_context.current

def turnSQLEchoOff():
    """Turn off echoing of SQL statements."""
    engine.echo = False

def turnSQLEchoOn():
    """Turn on echoing of SQL statements."""
    engine.echo = True

def vacuum(*tables):
    """Vacuum ``tables`` or all tables if ``tables`` not given."""
    connection.set_isolation_level(0)
    if not tables:
        cursor.execute('VACUUM FULL ANALYZE')
    else:
        for table in tables:
            cursor.execute('VACUUM FULL ANALYZE %s' % table)
    connection.set_isolation_level(2)

def execute(query):
    cursor.execute(query)

def commit():
    connection.commit()

def rollback():
    connection.rollback()

def dropSchema(schema, cascade=False):
    cascade_clause = ' CASCADE' if cascade else ''
    Q = 'DROP SCHEMA %s%s' % (schema, cascade_clause)
    try:
        execute(Q)
    except psycopg2.ProgrammingError:
        rollback()  # important!
    else:
        commit()

def createSchema(schema):
    Q = 'CREATE SCHEMA %s' % schema
    try:
        execute(Q)
    except psycopg2.ProgrammingError:
        rollback()  # important!
    else:
        commit()

def dropTable(table, cascade=False):
    # TODO: Try to make this work when the table has dependencies
    try:
        # FIXME: checkfirst doesn't seem to work
        if not cascade:
            table.drop(checkfirst=True)
        else:
            execute('DROP TABLE %s.%s CASCADE' % ((table.schema or 'public'),
                                                   table.name))
            commit()
    except (psycopg2.ProgrammingError, sqlalchemy.exceptions.SQLError), e:
        if 'does not exist' in str(e):
            rollback()
        else:
            raise e

def recreateTable(table):
    """Drop ``table`` from database and then create it."""
    dropTable(table)
    table.create()

def deleteAllFromTable(table):
    """Delete all records from ``table``."""
    try:
        table.delete().execute()
    except (psycopg2.ProgrammingError, sqlalchemy.exceptions.SQLError), e:
        if 'does not exist' in str(e):
            rollback()
        else:
            raise e

def addColumn(table_name, column_name, column_type):
    try:
        execute('ALTER TABLE %s ADD COLUMN %s %s' %
                   (table_name, column_name, column_type))
    except psycopg2.ProgrammingError, e:
        if 'already exists' not in str(e):
            raise e
    else:
        commit()

def dropColumn(table_name, column_name):
    try:
        execute('ALTER TABLE %s DROP COLUMN %s' % (table_name, column_name))
    except psycopg2.ProgrammingError, e:
        if 'already exists' not in str(e):
            raise e
    else:
        commit()

def getById(class_or_mapper, session, *ids):
    """Get objects and order by ``ids``.

    ``class_or_mapper`` Entity class or DB to object mapper
    ``session`` DB session
    ``ids`` One or more row IDs

    return `list`
      A list of domain objects corresponding to the IDs passed via ``ids``.
      Any ID in ``ids`` that doesn't correspond to a row in ``table`` will
      be ignored (for now), so the list may not contain the same number of
      objects as len(ids). If ``ids`` is empty, an empty list is returned.

    """
    query = session.query(class_or_mapper)
    objects = query.select(class_or_mapper.c.id.in_(*ids))
    objects_by_id = dict(zip([object.id for object in objects], objects))
    ordered_objects = []
    for i in ids:
        try:
            ordered_objects.append(objects_by_id[i])
        except KeyError:
            # No row with ID==i in ``table``
            # TODO: Should we insert None instead or raise???
            pass
    return ordered_objects


def addGeometryColumn(table, srid, geom_type, schema='public', name='geom'):
    """Add a PostGIS geometry column to ``table``.

    ``table``
        SQLAlchemy ``Table``

    ``srid``
        Spatial reference ID

    ``geom_type``
        POINT, LINESTRING, etc

    ``name``
        Name to give the new geometry column

    """
    # Add geometry columns after tables are created and add gist INDEXes them
    drop_col = 'ALTER TABLE "%s"."%s" DROP COLUMN %s'
    add_geom_col = "SELECT AddGeometryColumn('%s', '%s', '%s', %s, '%s', 2)"
    create_gist_index = ('CREATE INDEX "%s_%s_gist"'
                         'ON "%s"."%s"'
                         'USING GIST ("%s" gist_geometry_ops)')
    geom_type = geom_type.upper()
    try:
        execute(drop_col % (schema, table, name))
    except psycopg2.ProgrammingError:
        rollback()  # important!
    execute(add_geom_col % (schema, table, name, srid, geom_type))
    execute(create_gist_index % (table, name, schema, table, name))
    commit()

init()


if __name__ == '__main__':
    import sys
    from byCycle import model
    try:
        action = sys.argv[1]
    except IndexError:
        print 'No action'
    else:
        print 'Action: %s' % action
        try:
            args = sys.argv[2:]
        except IndexError:
            args = []
        model.db.connectMetadata()
        getattr(model.db, action)(*args)
