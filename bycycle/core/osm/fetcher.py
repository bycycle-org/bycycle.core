import os
from pathlib import Path

from urllib.request import urlretrieve


DEFAULT_URL = (
    'http://overpass-api.de/api/interpreter?data='
    '[out:json];'
    '{query};'
    'out;'
)


class OSMDataFetcher:

    """Fetch OSM data via Overpass API.

    Args:
        bbox (tuple): Bounding box
        path: Path to save data to
        query: Overpass API query or query type; pass a preset query
            type (highway or place) or a query

    """

    query_types = {
        'highways': '(way[highway]({bbox});>;)',
        'buildings': '(way[building]({bbox});>;)',
    }

    def __init__(self, bbox, path, query, url=DEFAULT_URL):
        # Convert bounding box to S, W, N, E as required by Overpass API.
        minx, miny, maxx, maxy = bbox
        bbox = miny, minx, maxy, maxx

        bbox_str = ','.join(str(f) for f in bbox)

        query = self.query_types.get(query, query)
        query = query.format(bbox=bbox_str)

        url = url or DEFAULT_URL
        url = url.format(query=query)

        self.bbox = bbox
        self.url = url
        self.path = Path(path).resolve()

    def run(self):
        def get_size_and_unit(size, gb=2 ** 30, mb=2 ** 20, kb=2 ** 10):
            unit = 'B'
            if size > gb:
                size, unit = size / gb, 'GB'
            elif size > mb:
                size, unit = size / mb, 'MB'
            elif size > kb:
                size, unit = size / kb, 'KB'
            return size, unit

        def show_progress(size, total_size):
            size, unit = get_size_and_unit(size)
            if total_size == -1:
                msg = '\r{size:.2f}{unit}'.format_map(locals())
            else:
                total_size, total_unit = get_size_and_unit(total_size)
                msg = '\r{size:.2f}{unit} of {total_size:.2f}{total_unit}'.format_map(locals())
            print(' ' * 20, '\r', msg, sep='', end='', flush=True)

        def hook(num_blocks, block_size, total_size):
            show_progress(num_blocks * block_size, total_size)

        self.path.parent.mkdir(parents=True, exist_ok=True)

        print('Fetching {self.url}...'.format_map(locals()), flush=True)
        urlretrieve(self.url, self.path, hook)
        stat = os.stat(self.path)
        show_progress(stat.st_size, stat.st_size)
        print('\nSaved to {self.path}'.format_map(locals()))
