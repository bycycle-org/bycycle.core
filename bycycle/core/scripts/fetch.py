import argparse

from tangled.converters import as_tuple_of

from bycycle.core.osm import OSMDataFetcher


as_tuple_of_float = as_tuple_of(float)


def fetch(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'bbox', type=as_tuple_of_float, help='BBOX as "minx miny maxx maxy"')
    parser.add_argument('file_name')
    parser.add_argument('--url')
    args = parser.parse_args(argv)
    kwargs = {}
    if args.url:
        kwargs['url'] = args.url
    fetcher = OSMDataFetcher(args.bbox, args.file_name, **kwargs)
    fetcher.run()
