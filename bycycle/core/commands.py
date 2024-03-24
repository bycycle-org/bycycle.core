import code
import csv
import datetime
import os.path
import shutil
import sys
import unittest
from getpass import getpass
from importlib import import_module
from pathlib import Path

from runcommands import arg, command
from runcommands.commands import local
from runcommands.util import abort, confirm, printer

from sqlalchemy.engine import create_engine as base_create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from bycycle.core.model import Base, MVTCache, USPSStreetSuffix
from bycycle.core.osm import OSMDataFetcher, OSMGraphBuilder, OSMImporter


__all__ = [
    'clean',
    'clear_mvt_cache',
    'db',
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
    'make_dist',
    'reload_graph',
    'shell',
    'test',
]


@command
def init():
    """Initialize project.

    Steps:

    - Install/upgrade packages
    - Create database
    - Create database schema
    - Load USPS street suffixes
    - Fetch OSM data
    - Load OSM data and create routing graph

    """
    install(upgrade=True)
    create_db()
    create_schema()
    load_usps_street_suffixes()
    fetch_osm_data()
    load_osm_data()


@command
def clean(all_=False):
    """Clean up.

    - Remove build directory
    - Remove dist directory
    - Remove __pycache__ directories

    If --all:

    - Remove egg-info directory
    - Remove .venv directory

    """
    def rmdir(directory, quiet=False):
        if directory.is_dir():
            shutil.rmtree(directory)
            if not quiet:
                printer.info('Removed directory:', directory)
        else:
            if not quiet:
                printer.warning('Directory does not exist:', directory)

    cwd = Path.cwd()

    rmdir(Path('./build'))
    rmdir(Path('./dist'))

    pycache_dirs = tuple(Path('.').glob('**/__pycache__/'))
    num_pycache_dirs = len(pycache_dirs)
    for pycache_dir in pycache_dirs:
        rmdir(pycache_dir, quiet=True)
    if num_pycache_dirs:
        printer.info(
            f'Removed {num_pycache_dirs} __pycache__'
            f'director{"y" if num_pycache_dirs == 1 else "ies"}')
    else:
        printer.warning('No __pycache__ directories found')

    if all_:
        rmdir(cwd / '.venv')
        rmdir(cwd / f'{cwd.name}.egg-info')


@command
def install(upgrade=False):
    if upgrade:
        local('.venv/bin/pip install --upgrade --upgrade-strategy eager pip setuptools')
        local('poetry update')
    else:
        local('poetry install')


@command
def test(*tests, coverage=True, verbose=False, fail_fast=False):
    top_level_dir = Path.cwd()

    where = top_level_dir
    for segment in top_level_dir.name.split('.'):
        where = where / segment

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


@command
def make_dist():
    local('poetry build')


@command
def shell():
    banner = 'byCycle Shell'
    try:
        import bpython
    except ImportError:
        printer.warning('bpython is not installed; falling back to python')
        code.interact(banner=banner)
    else:
        bpython.embed(banner=banner)


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
def dbshell(db):
    password = db.get('password')
    local((
        'docker', 'exec', '--interactive', '--tty',
        ('--env', f'PGPASSWORD="{password}"') if password else None,
        'bycycledocker_postgres_1',
        'psql',
        '--username', db['user'],
        '--host', db['host'],
        '--port', db['port'],
        '--dbname', db['database'],
    ))

@command
def db(data_dir="/opt/homebrew/var/postgresql@14"):
    """Run postgres locally."""
    local(("postgres", "-D", data_dir))


@command
def create_db(db, superuser='postgres', superuser_password='postgres',
              superuser_database='postgres', drop=False):
    owner = db['user']
    password = db.get('password')
    host = db['host']
    port = db['port']
    database = db['database']

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
        create_user_statement += ('WITH PASSWORD', f"'{password}'")

    execute(postgres_engine, ('DROP DATABASE', database), condition=drop)
    execute(postgres_engine, ('DROP USER', owner), condition=drop)
    execute(postgres_engine, create_user_statement)
    execute(postgres_engine, ('GRANT', owner, 'TO', superuser))
    execute(postgres_engine, ('CREATE DATABASE', database, 'OWNER', owner))

    postgres_engine.dispose()

    # Create extensions (connect to app database)

    app_engine = create_engine(database=database, **common_engine_args)

    execute(app_engine, 'CREATE EXTENSION postgis')

    app_engine.dispose()


@command
def drop_db(env, db, superuser='postgres', superuser_password='postgres',
            superuser_database='postgres',):
    if env == 'production':
        abort(1, 'Cannot drop production database')

    host = db['host']
    port = db['port']
    database = db['database']

    prompt = f'Drop database {database} via {superuser}@{host}?'
    if not confirm(prompt, yes_values=['yes']):
        abort()

    engine = create_engine(superuser, superuser_password, host, port, superuser_database)
    execute(engine, ('DROP DATABASE', database))


@command
def create_schema(db):
    engine = create_engine(**db)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


@command
def clear_mvt_cache(db):
    """Clear the MVT cache used in development.

    This may be necessary if the cache contains stale data.

    """
    engine = create_engine(**db)
    result = engine.execute(MVTCache.__table__.delete())
    count = result.rowcount
    ess = '' if count == 1 else 's'
    printer.success(f'{count} MVT cache record{ess} deleted')


@command
def load_usps_street_suffixes(db):
    """Load USPS street suffixes into database."""
    module = import_module('bycycle.core.model')
    base_path = os.path.dirname(module.__file__)
    path = os.path.join(base_path, 'usps_street_suffixes.csv')

    engine = create_engine(**db)
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
def fetch_osm_data(
    bbox: arg(type=float, nargs=4),
    directory='../osm',
    file_name=None,
    query='highways',
    url=None,
    log_to=None
):
    """Fetch OSM data and save to file.

    The bounding box must be passed as min X, min Y, max X, max Y.

    """
    if not file_name:
        file_name = f'{query}.json'
    path = Path(directory) / file_name
    fetcher = OSMDataFetcher(bbox, path, query, url)
    fetcher.run()
    if log_to:
        message = f'Saved OSM data from {fetcher.url} to {fetcher.path}'
        log_to_file(log_to, message)


@command
def load_osm_data(
    db,
    bbox: arg(type=float, nargs=4),
    directory='../osm',
    graph_path='../graph.marshal',
    streets=True,
    places=True,
    actions: arg(container=tuple, type=int) = (),
    show_actions: arg(short_option='-a') = False,
    log_to=None
):
    """Read OSM data from file and load into database."""
    importer = OSMImporter(bbox, directory, graph_path, db, streets, places, actions)
    if show_actions:
        printer.header('Available actions:')
        for action in importer.all_actions:
            printer.info(action)
        return
    importer.run()
    if log_to:
        message = f'Loaded OSM data from {importer.data_directory} to {importer.engine.url}'
        log_to_file(log_to, message)


@command
def create_graph(db, path='../graph.marshal', reload=True, log_to=None):
    """Read OSM data from database and write graph to path."""
    builder = OSMGraphBuilder(path, db)
    builder.run()
    if reload:
        reload_graph()
    if log_to:
        message = f'Created graph from {builder.engine.url} and saved to {path}'
        log_to_file(log_to, message)


@command
def reload_graph(log_to=None):
    # XXX: Only works if `dijkstar serve --workers=1`; if workers is
    #      greater than 1, the Dikstar server process must be restarted
    #      instead.
    local('curl -X POST "http://localhost:8000/reload-graph"')
    print()
    if log_to:
        message = f'Reloaded graph'
        log_to_file(log_to, message)


def log_to_file(file, line, with_timestamp=True):
    """Append line to file.

    If file is a single dash, write to stdout instead.

    """
    line = f'{line.rstrip()}\n'
    if with_timestamp:
        timestamp = datetime.datetime.now().isoformat()
        line = f'[{timestamp}] {line}'
    if file == '-':
        sys.stdout.write(line)
    else:
        path = Path(file)
        if not path.exists():
            path.touch(mode=0o664)
        with path.open('a') as fp:
            fp.write(line)
