import csv
import os
import unittest
from getpass import getpass

from runcommands import command
from runcommands.commands import local
from runcommands.util import abort, confirm, printer

from sqlalchemy.engine import create_engine as base_create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from tangled.util import asset_path

from bycycle.core.model import Base, MVTCache, USPSStreetSuffix
from bycycle.core.osm import OSMDataFetcher, OSMGraphBuilder, OSMImporter


__all__ = [
    'clear_mvt_cache',
    'create_db',
    'create_graph',
    'create_schema',
    'dbshell',
    'drop_db',
    'fetch_osm_data',
    'init',
    'install',
    'load_osm_data',
    'load_usps_street_suffixes',
    'test',
]


@command
def init():
    install(upgrade=True)
    create_db()
    create_schema()
    load_usps_street_suffixes()
    fetch_osm_data()
    load_osm_data()
    create_graph()


@command
def install(upgrade=False):
    if upgrade:
        local('poetry update')
    else:
        local('poetry install')


@command
def test(package, coverage=True, tests=(), verbose=False, fail_fast=False):
    cwd = os.getcwd()
    where = os.path.join(cwd, package.replace('.', os.sep))
    top_level_dir = cwd

    coverage = coverage and not tests
    verbosity = 2 if verbose else 1

    if coverage:
        from coverage import Coverage
        cover = Coverage(branch=True, source=[where])
        cover.start()

    loader = unittest.TestLoader()
    if tests:
        suite = loader.loadTestsFromNames(tests)
    else:
        suite = loader.discover(where, top_level_dir=top_level_dir)

    runner = unittest.TextTestRunner(verbosity=verbosity, failfast=fail_fast)
    runner.run(suite)

    if coverage:
        cover.stop()
        cover.report()


def create_engine(user, password, host='localhost', port=5432, database=None, driver='postgresql'):
    if password is None:
        password = getpass('Database password for {user}@{host}/{database}: '.format_map(locals()))

    url = URL(
        drivername=driver,
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )

    return base_create_engine(url, isolation_level='AUTOCOMMIT')


def execute(engine, sql, condition=True):
    if not condition:
        return
    if isinstance(sql, (list, tuple)):
        sql = ' '.join(sql)
    printer.info('Running SQL:', sql)
    try:
        return engine.execute(sql)
    except ProgrammingError as exc:
        error = str(exc.orig)
        exc_str = str(exc)
        if 'already exists' in exc_str or 'does not exist' in exc_str:
            printer.warning(exc.statement.strip(), error.strip(), sep=': ')
        else:
            raise


@command
def dbshell(user, password, database, host='localhost', port=5432):
    environ = {}
    if password:
        environ['PGPASSWORD'] = password
    local((
        'pgcli',
        '--user', user,
        '--host', host,
        '--port', port,
        '--dbname', database,
    ), environ=environ)


@command
def create_db(# Owner and database to create
              owner, password, database,
              # Postgres superuser used to run drop & create commands
              superuser='postgres', superuser_password='', superuser_database='postgres',
              host='localhost', port=5432, drop=False):
    common_engine_args = {
        'user': superuser,
        'password': superuser_password,
        'host': host,
        'port': port,
    }

    # Drop/create database/user (connect to postgres database)

    postgres_engine = create_engine(database=superuser_database, **common_engine_args)

    create_user_statement = ('CREATE USER', owner)
    if password:
        create_user_statement += ('WITH PASSWORD', password)

    execute(postgres_engine, ('DROP DATABASE', database), condition=drop)
    execute(postgres_engine, create_user_statement)
    execute(postgres_engine, ('GRANT', owner, 'TO', superuser))
    execute(postgres_engine, ('CREATE DATABASE', database, 'OWNER', owner))

    postgres_engine.dispose()

    # Create extensions (connect to app database)

    app_engine = create_engine(database=database, **common_engine_args)

    execute(app_engine, 'CREATE EXTENSION postgis')

    app_engine.dispose()


@command
def drop_db(env, database,
            superuser='postgres', superuser_password='', superuser_database='postgres',
            host='localhost', port=5432):
    if env == 'prod':
        abort(1, 'Cannot drop prod database')

    prompt = 'Drop database {database} via {user}@{host}?'.format_map(locals())
    if not confirm(prompt, yes_values=['yes']):
        abort()

    engine = create_engine(superuser, superuser_password, host, port, superuser_database)
    execute(engine, ('DROP DATABASE', database))


@command
def create_schema(user, password, database, host='localhost', port=5432):
    engine = create_engine(user, password, host, port, database)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


@command
def load_usps_street_suffixes(user, password, database, host='localhost', port=5432):
    """Load USPS street suffixes into database."""
    file_name = '{model.__tablename__}.csv'.format(model=USPSStreetSuffix)
    path = asset_path('bycycle.core.model', file_name)

    engine = create_engine(user, password, host, port, database)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    printer.info('Deleting existing USPS street suffixes...', end=' ')
    count = session.query(USPSStreetSuffix).delete()
    session.commit()
    printer.info(count, 'deleted')

    printer.info('Adding USPS street suffixes...', end=' ')
    with open(path) as fp:
        reader = csv.DictReader(fp)
        records = [USPSStreetSuffix(**row) for row in reader]
    count = len(records)
    session.add_all(records)
    session.commit()
    printer.info(count, 'added')

    session.close()
    engine.dispose()


@command
def clear_mvt_cache():
    """Clear the MVT cache used in development.

    This may be necessary if the cache contains stale data.

    """
    engine = create_engine('bycycle', '')
    result = engine.execute(MVTCache.__table__.delete())
    count = result.rowcount
    ess = '' if count == 1 else 's'
    printer.success(f'{count} MVT cache record{ess} deleted')


@command
def fetch_osm_data(bbox=(-122.7248, 45.4975, -122.6190, 45.5537), path='osm.data', url=None):
    """Fetch OSM data and save to file.

    The bounding box must be passed as min X, min Y, max X, max Y.

    """
    fetcher = OSMDataFetcher(bbox, path, 'highway', url)
    fetcher.run()


@command
def load_osm_data(db, path='osm.data', actions=()):
    """Read OSM data from file and load into database."""
    importer = OSMImporter(path, db, actions)
    importer.run()


@command
def create_graph(db, clean=True):
    """Read OSM data from database and write graph to path."""
    builder = OSMGraphBuilder(db, clean)
    builder.run()
