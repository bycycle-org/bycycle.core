import csv

from runcommands import command, commands
from runcommands.util import printer

from tangled.util import asset_path


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
def install(config):
    commands.local(config, '{venv.pip} install -r requirements.txt')


@command
def create_db(config, user='{db.user}', name='{db.name}', host='{db.host}', drop=False,
              drop_database=False, drop_user=False):
    drop_database = drop or drop_database
    drop_user = drop or drop_user

    def run_psql_command(sql, condition=True, database='postgres'):
        if not condition:
            return
        commands.local(config, (
            'psql',
            '--user postgres',
            '--host', host,
            '--dbname', database,
            '--command', f'"{sql};"',
        ), abort_on_failure=False)

    run_psql_command(f'DROP DATABASE {name}', condition=drop_database)
    run_psql_command(f'DROP USER {user}', condition=drop_user)
    run_psql_command(f'CREATE USER {user}')
    run_psql_command(f'CREATE DATABASE {name} OWNER {user}')
    run_psql_command(f'CREATE EXTENSION postgis', database=name)


@command
def create_schema(config):
    from bycycle.core.model import Base
    from sqlalchemy import create_engine
    engine = create_engine(config.db.url)
    Base.metadata.create_all(bind=engine)


@command
def load_usps_street_suffixes(config):
    """Load USPS street suffixes into database."""
    from sqlalchemy.engine import create_engine
    from sqlalchemy.orm import sessionmaker
    from bycycle.core.model.suffix import USPSStreetSuffix

    path = asset_path('bycycle.core.model', f'{USPSStreetSuffix.__tablename__}.csv')

    engine = create_engine(config.db.url)
    session = sessionmaker(bind=engine)()

    printer.info('Deleting existing USPS street suffixes...', end=' ')
    count = session.query(USPSStreetSuffix).delete()
    session.commit()
    printer.info(f'{count} deleted')

    printer.info('Adding USPS street suffixes...', end=' ')
    with open(path) as fp:
        reader = csv.DictReader(fp)
        records = [USPSStreetSuffix(**row) for row in reader]
    count = len(records)
    session.add_all(records)
    session.commit()
    printer.info(f'{count} added')


@command
def fetch_osm_data(config, url=None, path='osm.data',
                   minx=-122.7248, miny=45.4975, maxx=-122.6190, maxy=45.5537):
    """Fetch OSM data and save to file."""
    from bycycle.core.osm import OSMDataFetcher
    bbox = (minx, miny, maxx, maxy)
    fetcher = OSMDataFetcher(bbox, path, url)
    fetcher.run()


@command
def load_osm_data(config, path='osm.data', db_url='{db.url}', actions=()):
    """Read OSM data from file and load into database."""
    from bycycle.core.osm import OSMImporter
    db_url = db_url.format_map(config)
    importer = OSMImporter(path, db_url, actions)
    importer.run()


@command
def create_graph(config, db_url='{db.url}', path='bycycle.core:matrix'):
    """Read OSM data from database and write graph to path."""
    from bycycle.core.osm import OSMGraphBuilder
    db_url = db_url.format_map(config)
    path = asset_path(path)
    builder = OSMGraphBuilder(db_url, path)
    builder.run()
