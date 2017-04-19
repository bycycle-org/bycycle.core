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
                msg = f'\r{size}B'
            else:
                msg = f'\r{size}B of {total_size}B'
            print(msg, end='', flush=True)
        print(f'Fetching {self.url}...', flush=True)
        urlretrieve(self.url, self.file_name, hook)
        print(f'\nSaved to {self.file_name}')
