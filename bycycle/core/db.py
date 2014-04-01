"""Database connection initialization and handling.

Provides the ``DB`` class, which connects to the database and contains various
generic (i.e., not region-specific) database functions.

"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL


engine = None
session_factory = None


def init(**connection_args):
    global engine, session_factory
    engine = create_engine(make_url(**connection_args))
    session_factory = sessionmaker(bind=engine)


def make_session():
    return session_factory()


def make_url(drivername='postgresql', database='bycycle', **kwargs):
    return URL(drivername, database=database, **kwargs)
