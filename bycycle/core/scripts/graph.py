import argparse

from bycycle.core.osm import OSMGraphBuilder


def make_graph(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('file_name', help='Output file name')
    parser.add_argument('db_url')
    args = parser.parse_args(argv)
    graph_builder = OSMGraphBuilder(args.file_name, args.db_url)
    graph_builder.run()
