from urllib.request import urlretrieve


DEFAULT_URL = 'http://www.overpass-api.de/api/xapi?way[highway=*][bbox={}]'


class OSMDataFetcher:

    """Fetch OSM data inside a bounding box."""

    def __init__(self, bbox, file_name, url=DEFAULT_URL):
        if url is None:
            url = DEFAULT_URL
        self.bbox = bbox
        bbox = ','.join(str(f) for f in bbox)
        self.url = url.format(bbox)
        self.file_name = file_name

    def run(self):
        def hook(num_blocks, block_size, total_size):
            size = num_blocks * block_size
            if total_size == -1:
                msg = '\r{size}B'.format_map(locals())
            else:
                msg = '\r{size}B of {total_size}B'.format_map(locals())
            print(msg, end='', flush=True)
        print('Fetching {self.url}...'.format_map(locals()), flush=True)
        urlretrieve(self.url, self.file_name, hook)
        print('\nSaved to {self.file_name}'.format_map(locals()))
