"""Route entity."""
from shapely.geometry import LineString, mapping

import glineenc

from bycycle.core.model.entities.base import Entity


__all__ = ['Route']


class Route(Entity):
    """Represents a route between two addresses."""

    member_name = 'route'
    collection_name = 'routes'
    member_title = 'Route'
    collection_title = 'Routes'

    def __init__(self,
                 region,
                 start, end,
                 directions, linestring, distance):
        self.region = region
        self.start = start
        self.end = end
        self.directions = directions
        self.distance = distance
        self.linestring = linestring
        if linestring is not None:
            xs, ys = zip(*self.linestring.coords)
            xs, ys = region.proj(xs, ys, inverse=True)
            self.linestring_lat_long = LineString(zip(xs, ys))
        else:
            self.linestring_lat_long = None

    def to_simple_object(self, fields=None):
        linestring = self.linestring_lat_long
        envelope = linestring.envelope
        centroid = envelope.centroid
        minx, miny, maxx, maxy = envelope.bounds
        route = {
            'start': self.start.to_simple_object(),
            'end': self.end.to_simple_object(),
            'linestring': mapping(linestring),
            'bounds': {
                'sw': {'x': minx, 'y': miny},
                'ne': {'x': maxx, 'y': maxy}
            },
            'center': {'x': centroid.x, 'y': centroid.y},
            'directions': self.directions,
            'distance': self.distance,
        }
        # Encode line for Google Map
        pairs = [(y, x) for (x, y) in linestring.coords]
        points, levels = glineenc.encode_pairs(pairs)
        route['google_points'] = points
        route['google_levels'] = levels
        return route

    def __repr__(self):
        return repr(self.to_simple_object())

    def __str__(self):
        directions = []
        for d in self.directions:
            dbm = d['bikemode']
            bm = [', '.join([[b, '-'][b is 'n'] for b in dbm]), ''][not dbm]
            directions.append('%s on %s toward %s -- %s %s [%s]' % (
                d['turn'],
                d['street'],
                d['toward'],
                '%.2f' % (d['distance']['miles']),
                'miles',
                bm,
            ))
        directions = '\n'.join([
            '%s%s. %s' % (['', ' '][i<10], i, d)
            for i, d
            in enumerate(directions)
        ])
        s = [
            self.start['geocode'],
            self.end['geocode'],
            'Distance: %.2f' % (self.distance['miles']),
            directions,
        ]
        return '\n'.join([str(a) for a in s])
