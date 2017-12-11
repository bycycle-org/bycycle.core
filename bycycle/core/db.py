"""Database connection/session initialization.

Used internally for scripts and tests.

"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL


engine = None
session_factory = None


def init(**connection_args):
    global engine, session_factory
    if engine is None:
        engine = create_engine(make_url(**connection_args))
        session_factory = sessionmaker(bind=engine)
    return engine, session_factory


def make_url(drivername='postgresql', user='bycycle', host='localhost', database='bycycle', **kwargs):
    return URL(drivername, username=user, host=host, database=database, **kwargs)
