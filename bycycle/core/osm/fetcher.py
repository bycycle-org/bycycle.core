import os

from urllib.request import urlretrieve


DEFAULT_URL = (
    'http://overpass-api.de/api/interpreter?data='
    '[out:json];'
    'way[highway]({bbox});'
    '<;>;'
    'out;'
)


class OSMDataFetcher:

    """Fetch OSM data inside a bounding box.

    .. note:: BBOX order is S, W, N, E

    """

    def __init__(self, bbox, file_name, url=DEFAULT_URL):
        url = url or DEFAULT_URL
        self.bbox = bbox
        self.bbox_str = ','.join(str(f) for f in bbox)
        self.url = url.format(bbox=self.bbox_str)
        self.file_name = file_name

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

        print('Fetching {self.url}...'.format_map(locals()), flush=True)
        urlretrieve(self.url, self.file_name, hook)
        stat = os.stat(self.file_name)
        show_progress(stat.st_size, stat.st_size)
        print('\nSaved to {self.file_name}'.format_map(locals()))
