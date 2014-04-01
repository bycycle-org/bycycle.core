from urllib.request import urlretrieve


DEFAULT_URL = 'http://www.overpass-api.de/api/xapi?way[highway=*][bbox={}]'


class OSMDataFetcher:

    """Fetch OSM data inside a bounding box."""

    def __init__(self, bbox, file_name, url=DEFAULT_URL):
        self.bbox = bbox
        bbox = ','.join(str(f) for f in bbox)
        self.url = url.format(bbox)
        self.file_name = file_name

    def run(self):
        urlretrieve(self.url, self.file_name)
