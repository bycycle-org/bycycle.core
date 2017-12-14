import csv

from runcommands import command
from runcommands.commands import local
from runcommands.util import get_all_list, printer

from sqlalchemy.engine import create_engine
from sqlalchemy.exc import ProgrammingError

from tangled.commands import test
from tangled.util import asset_path

from bycycle.core import db
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


@command
def create_db(config,
              # Owner and database to create
              owner=None, database=None,
              # Postgres superuser used to run drop & create commands
              superuser='postgres', superuser_password=None, superuser_database='postgres',
              host=None, drop=False, drop_database=False, drop_user=False):
    owner = owner or config.db.user
    database = database or config.db.database
    drop_database = drop or drop_database
    drop_user = drop or drop_user

    f = locals()

    def execute(engine, sql, condition=True, format_map=f):
        if not condition:
            return
        try:
            engine.execute(sql.format_map(format_map))
        except ProgrammingError as exc:
            error = str(exc.orig)
            exc_str = str(exc)
            if 'already exists' in exc_str or 'does not exist' in exc_str:
                printer.warning(exc.statement.strip(), error.strip(), sep=': ')
            else:
                raise

    common_cxn_args = dict(user=superuser, password=superuser_password, host=host)
    common_engine_args = dict(isolation_level='AUTOCOMMIT')

    # Drop/create database/user (connect to postgres database)

    cxn_args = get_db_init_args(config, database=superuser_database, **common_cxn_args)
    postgres_engine = create_engine(db.make_url(**cxn_args), **common_engine_args)

    execute(postgres_engine, 'DROP DATABASE {database}', condition=drop_database)
    execute(postgres_engine, 'DROP USER {owner}', condition=drop_user)
    execute(postgres_engine, 'CREATE USER {owner}')
    execute(postgres_engine, 'CREATE DATABASE {database} OWNER {owner}')

    postgres_engine.dispose()

    # Create extensions (connect to app database)

    cxn_args = get_db_init_args(config, database=database, **common_cxn_args)
    app_engine = create_engine(db.make_url(**cxn_args), **common_engine_args)

    execute(app_engine, 'CREATE EXTENSION postgis')

    app_engine.dispose()


@command
def create_schema(config):
    engine, _ = db.init(**get_db_init_args(config))
    Base.metadata.create_all(bind=engine)


@command
def load_usps_street_suffixes(config):
    """Load USPS street suffixes into database."""
    file_name = '{model.__tablename__}.csv'.format(model=USPSStreetSuffix)
    path = asset_path('bycycle.core.model', file_name)

    engine, session_factory = db.init(**get_db_init_args(config))
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


@command
def fetch_osm_data(config, url=None, path='osm.data',
                   minx=-122.7248, miny=45.4975, maxx=-122.6190, maxy=45.5537):
    """Fetch OSM data and save to file."""
    # Bounding box is S, W, N, E as required by Overpass API
    bbox = miny, minx, maxy, maxx
    fetcher = OSMDataFetcher(bbox, path, url)
    fetcher.run()


@command
def load_osm_data(config, path='osm.data', db_url='{db.url}', actions=()):
    """Read OSM data from file and load into database."""
    db_url = db_url.format_map(config)
    importer = OSMImporter(path, db_url, actions)
    importer.run()


@command
def create_graph(config, db_url='{db.url}', path='bycycle.core:matrix'):
    """Read OSM data from database and write graph to path."""
    db_url = db_url.format_map(config)
    path = asset_path(path)
    builder = OSMGraphBuilder(db_url, path)
    builder.run()


def get_db_init_args(config, **overrides):
    connection_args = {k: v for (k, v) in config.db.items()}
    connection_args.pop('url')
    for name, value in ((k, v) for (k, v) in overrides.items() if v):
        connection_args[name] = value
    return connection_args


__all__ = get_all_list(vars()) + ['test']
