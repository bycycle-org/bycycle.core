###############################################################################
# $Id: geocode.py 212 2006-09-11 04:16:40Z bycycle $
# Created 2006-09-25.
#
# Route entity.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Route entity."""
from shapely.geometry import LineString

from byCycle.model import glineenc

__all__ = ['Route']


class Route(object):
    """Represents a route between two addresses."""

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
        self.linestring_ll = LineString(region.proj(linestring.coords, inverse=True))

    def to_simple_object(self):
        coords = self.linestring.coords
        points = []
        for i in range(len(coords)):
            points.append(coords(i))
        linestring = [{'x': p[0], 'y': p[1]} for p in points]
        pairs = [(p[0], p[1]) for p in points]
        bounds = self.linestring.envelope()
        centroid = bounds.centroid()
        route = {
            'start': dict(self.start),
            'end': dict(self.end),
            'linestring': linestring,
            'bounds': {
                'sw': {'x': bounds.minx, 'y': bounds.miny},
                'ne': {'x': bounds.maxx, 'y': bounds.maxy}
            },
            'center': {'x': centroid.x, 'y': centroid.y},
            'directions': self.directions,
            'distance': self.distance,
        }
        if self.region.map_type == 'google':
            google_points, google_levels = glineenc.encode_pairs(pairs)
            route['google_points'] = google_points
            route['google_levels'] = google_levels
        route['start']['geocode'] = route['start']['geocode'].to_simple_object()
        route['end']['geocode'] = route['end']['geocode'].to_simple_object()
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
