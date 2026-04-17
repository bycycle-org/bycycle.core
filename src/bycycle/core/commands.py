import csv
import datetime
import os
import shutil
import sys
import unittest
from pathlib import Path
from typing import Annotated

from runcommands import arg, command
from runcommands.commands import local
from runcommands.util import abort, find_project_root, printer

from .util import django_setup

__all__ = [
    "clean",
    "clear_mvt_cache",
    "db",
    "django",
    "create_db",
    "create_graph",
    "fetch_osm_data",
    "format_code",
    "init",
    "install",
    "load_osm_data",
    "load_usps_street_suffixes",
    "reload_graph",
    "test",
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
                printer.info("Removed directory:", directory)
        else:
            if not quiet:
                printer.warning("Directory does not exist:", directory)

    cwd = Path.cwd()

    rmdir(Path("./build"))
    rmdir(Path("./dist"))

    pycache_dirs = tuple(Path(".").glob("**/__pycache__/"))
    num_pycache_dirs = len(pycache_dirs)
    for pycache_dir in pycache_dirs:
        rmdir(pycache_dir, quiet=True)
    if num_pycache_dirs:
        printer.info(
            f"Removed {num_pycache_dirs} __pycache__"
            f"director{'y' if num_pycache_dirs == 1 else 'ies'}"
        )
    else:
        printer.warning("No __pycache__ directories found")

    if all_:
        rmdir(cwd / ".venv")
        rmdir(cwd / f"{cwd.name}.egg-info")


@command
def install(upgrade=False):
    args = ["uv", "sync"]
    if upgrade:
        args.append("--upgrade")
    local(args)


@command
def test(
        *tests: Annotated[
            str,
            arg(help="Specific tests to run"),
        ],
        fail_fast=False,
        verbosity=1,
        with_coverage: Annotated[
            bool,
            arg(short_option="-c"),
        ] = True,
):
    django_setup()

    top_level_dir = find_project_root()
    os.chdir(top_level_dir)

    if tests:
        num_tests = len(tests)
        s = "" if num_tests == 1 else "s"
        printer.hr(f"Running {num_tests} test{s}")
    else:
        coverage_message = " with coverage" if with_coverage else ""
        printer.hr(f"Running tests{coverage_message}")

    runner = unittest.TextTestRunner(failfast=fail_fast, verbosity=verbosity)
    loader = unittest.TestLoader()

    coverage = None

    if with_coverage:
        from coverage import Coverage

        source_dir = str(top_level_dir / "src/runcommands")
        coverage = Coverage(source=[source_dir])
        coverage.start()

    if tests:
        sys.path.insert(0, str(top_level_dir))
        runner.run(loader.loadTestsFromNames(tests))
    else:
        tests_dir = str(top_level_dir / "tests")
        top_level_dir = str(top_level_dir)
        discovered_tests = loader.discover(tests_dir, top_level_dir=top_level_dir)
        result = runner.run(discovered_tests)
        if not result.errors:
            if coverage is not None:
                coverage.stop()
                coverage.report()


@command
def format_code(check=False, where="./"):
    if check:
        printer.header("Checking code formatting...")
        check_arg = "--check"
        raise_on_error = False
    else:
        printer.header("Formatting code...")
        check_arg = None
        raise_on_error = True
    result = local(("ruff", "format", check_arg, where), raise_on_error=raise_on_error)
    return result


@command
def django(
        *args: Annotated[
            str,
            arg(help="Django command, args, and options (specify options after --)"),
        ],
):
    """Run a Django command

    Runs `django-admin` with `DJANGO_SETTINGS_MODULE` set to `bycycle.core.settings`.

    Options for the Django command must be specified after `--`:

        run django migrate -- --help

    """
    local(
        ("uv", "run", "django-admin", *args),
        environ={"DJANGO_SETTINGS_MODULE": "bycycle.core.settings"},
        echo=True,
    )


# Database -------------------------------------------------------------


@command
def create_db(
        name="bycycle",
        postgres_bin: Annotated[
            str | None,
            arg(envvar="BYCYCLE_POSTGRES_BIN"),
        ] = None,
):
    """Create local byCycle database."""
    commands = [
        f"{postgres_bin}createuser --login {name}",
        f"{postgres_bin}createdb --owner {name} {name}",
        f"{postgres_bin}psql -c 'create extension postgis' {name}",
    ]
    for cmd in commands:
        printer.info(cmd)
        result = local(cmd, stderr="capture", raise_on_error=False)
        if result.failed:
            if "exists" in result.stderr:
                printer.print("[red]exists[/red]:", cmd)
            else:
                abort(1, result.stderr)
        else:
            printer.success("Done")


@command
def db(
        postgres_bin: Annotated[str | None, arg(envvar="BYCYCLE_POSTGRES_BIN")] = None,
        postgres_data: Annotated[
            str | None, arg(envvar="BYCYCLE_POSTGRES_DATA_DIR")
        ] = None,
):
    """Run postgres locally."""
    if not postgres_data:
        abort(1, "Postgres data directory is required")
    local((f"{postgres_bin}postgres", "-D", postgres_data))


@command
def clear_mvt_cache():
    """Clear the MVT cache used in development.

    This may be necessary if the cache contains stale data.

    """
    django_setup()

    from . import models

    count = models.MVTCache.objects.all().delete()
    ess = "" if count == 1 else "s"
    printer.success(f"{count} MVT cache record{ess} deleted")


@command
def load_usps_street_suffixes():
    """Load USPS street suffixes into database."""
    django_setup()

    from . import models

    if models.__file__ is None:
        abort(1, f"Module file not set for module: {models}")

    base_path = Path(models.__file__).parent
    path = base_path / "usps_street_suffixes.csv"

    printer.info("Deleting existing USPS street suffixes...", end=" ")
    count = models.USPSStreetSuffix.objects.all().delete()
    printer.info(count, "deleted")

    printer.info("Adding USPS street suffixes...", end=" ")
    with open(path) as fp:
        reader = csv.DictReader(fp)
        records = [models.USPSStreetSuffix(**row) for row in reader]
    models.USPSStreetSuffix.objects.bulk_create(records)
    count = len(records)
    printer.info(count, "added")


@command
def fetch_osm_data(
        bbox: arg(type=float, nargs=4),
        directory="../osm",
        file_name=None,
        query="highways",
        url=None,
        log_to=None,
):
    """Fetch OSM data and save to file.

    The bounding box must be passed as min X, min Y, max X, max Y.

    """
    django_setup()
    from . import osm

    if not file_name:
        file_name = f"{query}.json"
    path = Path(directory) / file_name
    fetcher = osm.OSMDataFetcher(bbox, path, query, url)
    fetcher.run()
    if log_to:
        message = f"Saved OSM data from {fetcher.url} to {fetcher.path}"
        log_to_file(log_to, message)


@command
def load_osm_data(
        bbox: Annotated[float, arg(type=float, nargs=4)],
        directory="../osm",
        graph_path="../graph.marshal",
        streets=True,
        places=True,
        actions: Annotated[tuple[int, ...], arg(container=tuple, type=int)] = (),
        show_actions: Annotated[bool, arg(short_option="-a")] = False,
        log_to=None,
):
    """Read OSM data from file and load into database."""
    django_setup()
    from . import osm

    importer = osm.OSMImporter(bbox, directory, graph_path, streets, places, actions)
    if show_actions:
        printer.header("Available actions:")
        for action in importer.all_actions:
            printer.info(action)
        return
    importer.run()
    if log_to:
        message = (
            f"Loaded OSM data from {importer.data_directory} to {importer.engine.url}"
        )
        log_to_file(log_to, message)


@command
def create_graph(path="../graph.marshal", reload=True, log_to=None):
    """Read OSM data from database and write graph to path."""
    django_setup()
    from . import osm

    builder = osm.OSMGraphBuilder(path)
    builder.run()
    if reload:
        reload_graph()
    if log_to:
        message = f"Saved graph to {path}"
        log_to_file(log_to, message)


@command
def reload_graph(log_to=None):
    # XXX: Only works if `dijkstar serve --workers=1`; if workers is
    #      greater than 1, the Dikstar server process must be restarted
    #      instead.
    local('curl -X POST "http://localhost:8000/reload-graph"')
    print()
    if log_to:
        message = f"Reloaded graph"
        log_to_file(log_to, message)


# Utilities ------------------------------------------------------------


def log_to_file(file, line, with_timestamp=True):
    """Append line to file.

    If file is a single dash, write to stdout instead.

    """
    line = f"{line.rstrip()}\n"
    if with_timestamp:
        timestamp = datetime.datetime.now().isoformat()
        line = f"[{timestamp}] {line}"
    if file == "-":
        sys.stdout.write(line)
    else:
        path = Path(file)
        if not path.exists():
            path.touch(mode=0o664)
        with path.open("a") as fp:
            fp.write(line)
