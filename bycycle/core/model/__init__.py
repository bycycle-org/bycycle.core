import inspect

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import configure_mappers, sessionmaker

from .base import Base, Entity
from .graph import Graph
from .intersection import Intersection
from .lookup import LookupResult
from .mvt import MVTCache
from .route import Route
from .street import Street
from .suffix import USPSStreetSuffix


configure_mappers()


def get_engine(**kwargs):
    url_kwargs = {}
    url_params = make_url.signature.parameters
    for name in tuple(kwargs):
        if name in url_params:
            url_kwargs[name] = kwargs.pop(name)
    url = make_url(**url_kwargs)
    return create_engine(url, **kwargs)


def make_url(driver='postgresql', user='bycycle', password=None, host='localhost', port=None,
             database='bycycle', query=None):
    return URL(
        driver, username=user, password=password, host=host, port=port, database=database,
        query=query)


make_url.signature = inspect.signature(make_url)


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    return factory


__all__ = [
    name for (name, obj) in globals().items()
    if (
        not name.startswith('_') and
        hasattr(obj, '__module__') and
        obj.__module__.startswith(__name__)
    )
]
