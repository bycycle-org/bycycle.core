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
from cartography.proj import SpatialReference
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

        linestring.srs = SpatialReference(epsg=region.srid)
        self.linestring = linestring

        linestring_ll = linestring.copy()
        ll_srs = SpatialReference(epsg=4326)
        linestring_ll.transform(src_proj=str(self.linestring.srs),
                                dst_proj=str(ll_srs))
        self.linestring_ll = linestring_ll

    def to_builtin(self):
        points = []
        for i in range(self.linestring_ll.numPoints()):
            points.append(self.linestring_ll.pointN(i))
        linestring = [{'x': p.x, 'y': p.y} for p in points]
        pairs = [(p.y, p.x) for p in points]
        bounds = self.linestring_ll.envelope()
        centroid = bounds.centroid()
        google_points, google_levels = glineenc.encode_pairs(pairs)
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
            'google_points': google_points,
            'google_levels': google_levels,
        }
        route['start']['geocode'] = route['start']['geocode'].to_builtin()
        route['end']['geocode'] = route['end']['geocode'].to_builtin()
        return route

    def __repr__(self):
        return repr(self.to_builtin())

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
