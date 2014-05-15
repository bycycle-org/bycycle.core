import argparse

from bycycle.core.osm import OSMDataFetcher


def fetch(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('minx', type=float)
    parser.add_argument('miny', type=float)
    parser.add_argument('maxx', type=float)
    parser.add_argument('maxy', type=float)
    parser.add_argument('file_name')
    parser.add_argument('--url')
    args = parser.parse_args(argv)
    kwargs = {}
    if args.url:
        kwargs['url'] = args.url
    bbox = [args.minx, args.miny, args.maxx, args.maxy]
    fetcher = OSMDataFetcher(bbox, args.file_name, **kwargs)
    print('Fetching {0.url}'.format(fetcher))
    fetcher.run()
