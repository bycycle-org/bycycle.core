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
