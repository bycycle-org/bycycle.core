import argparse

from bycycle.core.osm import OSMGraphBuilder


def make_graph(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('db_url')
    parser.add_argument('file_name', help='Output file name')
    args = parser.parse_args(argv)
    graph_builder = OSMGraphBuilder(args.db_url, args.file_name)
    graph_builder.run()
