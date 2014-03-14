"""Database connection initialization and handling.

Provides the ``DB`` class, which connects to the database and contains various
generic (i.e., not region-specific) database functions.

"""
import psycopg2
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError


metadata = MetaData()
engine = None
connection = None
cursor = None
session_factory = None


def init(**connection_args):
    global engine, connection, cursor, session_factory
    engine = create_engine(make_url(**connection_args))
    metadata.bind = engine
    connection = engine.raw_connection()
    cursor = connection.cursor()
    session_factory = sessionmaker(
        autoflush=True, autocommit=True, bind=engine)


def make_session():
    return session_factory()


def make_url(drivername='postgresql', database='bycycle', **kwargs):
    return URL(drivername, database=database, **kwargs)


def dropAllTables(md=None):
    md = md or metadata
    md.drop_all()


def createAllTables(md=None):
    md = md or metadata
    md.create_all()


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
            execute(
                'DROP TABLE %s.%s CASCADE' %
                ((table.schema or 'public'), table.name))
            commit()
    except (psycopg2.ProgrammingError, SQLAlchemyError) as e:
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
    except (psycopg2.ProgrammingError, SQLAlchemyError) as e:
        if 'does not exist' in str(e):
            rollback()
        else:
            raise e


def addColumn(table_name, column_name, column_type):
    try:
        execute(
            'ALTER TABLE %s ADD COLUMN %s %s' %
            (table_name, column_name, column_type))
    except psycopg2.ProgrammingErroras as e:
        if 'already exists' not in str(e):
            raise e
    else:
        commit()


def dropColumn(table_name, column_name):
    try:
        execute('ALTER TABLE %s DROP COLUMN %s' % (table_name, column_name))
    except psycopg2.ProgrammingErroras as e:
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


if __name__ == '__main__':
    import sys
    from bycycle.core import model
    try:
        action = sys.argv[1]
    except IndexError:
        print('No action')
    else:
        print('Action: %s' % action)
        try:
            args = sys.argv[2:]
        except IndexError:
            args = []
        getattr(model.db, action)(*args)
