import csv

from runcommands import command
from runcommands.commands import local
from runcommands.util import printer

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

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


@command
def create_db(config, user='{db.user}', name='{db.name}', host='{db.host}', drop=False,
              drop_database=False, drop_user=False):
    drop_database = drop or drop_database
    drop_user = drop or drop_user

    def run_psql_command(sql, condition=True, database='postgres'):
        if not condition:
            return
        local(config, (
            'psql',
            '--user postgres',
            '--host', host,
            '--dbname', database,
            '--command', '"{sql};"'.format(sql=sql),
        ), abort_on_failure=False)

    f = locals()
    run_psql_command('DROP DATABASE {name}'.format_map(f), condition=drop_database)
    run_psql_command('DROP USER {user}'.format_map(f), condition=drop_user)
    run_psql_command('CREATE USER {user}'.format_map(f))
    run_psql_command('CREATE DATABASE {name} OWNER {user}'.format_map(f))
    run_psql_command('CREATE EXTENSION postgis'.format_map(f), database=name)


@command
def create_schema(config):
    engine = create_engine(config.db.url)
    Base.metadata.create_all(bind=engine)


@command
def load_usps_street_suffixes(config):
    """Load USPS street suffixes into database."""
    file_name = '{model.__tablename__}.csv'.format(model=USPSStreetSuffix)
    path = asset_path('bycycle.core.model', file_name)

    engine = create_engine(config.db.url)
    session = sessionmaker(bind=engine)()

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
    bbox = (minx, miny, maxx, maxy)
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
