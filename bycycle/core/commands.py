import csv
from getpass import getpass

from runcommands import command
from runcommands.commands import local
from runcommands.util import abort, confirm, get_all_list, printer

from sqlalchemy.engine import create_engine as base_create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from tangled.commands import test
from tangled.util import asset_path

from bycycle.core.model import Base
from bycycle.core.model.suffix import USPSStreetSuffix
from bycycle.core.osm import OSMDataFetcher, OSMGraphBuilder, OSMImporter


@command
def init(config):
    install(config)
    create_db(config)
    create_schema(config)
    load_usps_street_suffixes(config)
    fetch_osm_data(config)
    load_osm_data(config)
    create_graph(config)


@command
def install(config, upgrade=False):
    local(config, (
        '{venv.pip} install',
        '--upgrade' if upgrade else '',
        '-r requirements.txt',
    ))


def create_engine(config, user=None, password=None, host=None, port=None, database=None):
    user = user or config.db.get('user')
    password = password or config.db.get('password')
    host = host or config.db.get('host')
    port = port or config.db.get('port', 5432)
    database = database or config.db.get('database')

    if password is None:
        password = getpass('Database password for {user}@{host}/{name}: '.format_map(locals()))

    url = URL(
        drivername='postgresql',
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


@command(default_env='development')
def create_db(config,
              # Owner and database to create
              owner=None, password=None, database=None,
              # Postgres superuser used to run drop & create commands
              superuser='postgres', superuser_password=None, superuser_database='postgres',
              host=None, port=None, drop=False):
    owner = owner or config.db.get('user')
    password = password or config.db.get('password')
    host = host or config.db.get('host')

    database = database or config.db['database']

    common_engine_args = {
        'user': superuser,
        'password': superuser_password,
        'host': host,
        'port': port,
    }

    # Drop/create database/user (connect to postgres database)

    postgres_engine = create_engine(config, database=superuser_database, **common_engine_args)

    create_user_statement = ('CREATE USER', owner)
    if password:
        create_user_statement += ('WITH PASSWORD', password)

    execute(postgres_engine, ('DROP DATABASE', database), condition=drop)
    execute(postgres_engine, create_user_statement)
    execute(postgres_engine, ('GRANT', owner, 'TO', superuser))
    execute(postgres_engine, ('CREATE DATABASE', database, 'OWNER', owner))

    postgres_engine.dispose()

    # Create extensions (connect to app database)

    app_engine = create_engine(config, database=database, **common_engine_args)

    execute(app_engine, 'CREATE EXTENSION postgis')

    app_engine.dispose()


@command(default_env='development')
def drop_db(config, user='postgres', password=None, host=None, port=None, database=None):
    if config.env == 'prod':
        abort(1, 'Cannot drop prod database')

    database = database or config.db['database']

    prompt = 'Drop database {database}?'.format_map(locals())
    if not confirm(config, prompt, yes_values=['yes']):
        abort()

    engine = create_engine(config, user, password, host, port, 'postgres')
    execute(engine, 'DROP DATABASE {database}'.format_map(locals()))


@command
def create_schema(config):
    engine = create_engine(config)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


@command
def load_usps_street_suffixes(config):
    """Load USPS street suffixes into database."""
    file_name = '{model.__tablename__}.csv'.format(model=USPSStreetSuffix)
    path = asset_path('bycycle.core.model', file_name)

    engine = create_engine(config)
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
def fetch_osm_data(config, bbox, url=None, path='{bycycle.osm.data_path}'):
    """Fetch OSM data and save to file.

    The bounding box must be passed as min X, min Y, max X, max Y.

    """
    path = path.format_map(config)

    # Convert bounding box to S, W, N, E as required by Overpass API.
    minx, miny, maxx, maxy = bbox
    bbox = miny, minx, maxy, maxx

    fetcher = OSMDataFetcher(bbox, path, url)
    fetcher.run()


@command
def load_osm_data(config, path='{bycycle.osm.data_path}', actions=()):
    """Read OSM data from file and load into database."""
    path = path.format_map(config)
    connection_args = {k: v for (k, v) in config.db.items()}
    importer = OSMImporter(path, connection_args, actions)
    importer.run()


@command
def create_graph(config, clean=True):
    """Read OSM data from database and write graph to path."""
    connection_args = {k: v for (k, v) in config.db.items()}
    builder = OSMGraphBuilder(connection_args, clean)
    builder.run()


__all__ = get_all_list(vars()) + ['test']
