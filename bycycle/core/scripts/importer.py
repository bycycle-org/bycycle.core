import argparse

from tangled.converters import as_tuple_of

from bycycle.core.osm import OSMImporter


as_tuple_of_float = as_tuple_of(float)


def do_import(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('file_name')
    parser.add_argument('db_url')
    parser.add_argument('-a', '--action', type=int, action='append')
    args = parser.parse_args(argv)
    importer = OSMImporter(args.file_name, args.db_url, actions=args.action)
    importer.run()
