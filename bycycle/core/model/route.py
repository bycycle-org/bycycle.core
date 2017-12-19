import glineenc

from . import Entity


class Route(Entity):

    def __init__(self, start, end, directions, linestring, distance):
        self.id = ';'.join((start.id, end.id))
        self.name = ' to '.join(name for name in (start.name, end.name) if name)
        self.start = start
        self.end = end
        self.directions = directions
        self.distance = distance
        self.bounds = linestring.bounds
        self.linestring = linestring
        pairs = [(y, x) for (x, y) in linestring.coords]
        points, levels = glineenc.encode_pairs(pairs)
        self.linestring_encoded = points
        self.linestring_encoded_levels = levels

    def __str__(self):
        template = '{}{i}. {turn} on {street} toward {toward} -- {miles} miles'
        directions = []
        for i, d in enumerate(self.directions):
            spacer = ' ' if i < 10 else ''
            directions.append(
                template.format(spacer, i=i, miles=d['distance']['miles'], **d))
        directions = '\n'.join(directions)
        distance = 'Distance: {:.2f}'.format(self.distance['miles'])
        return '\n'.join(
            str(a)
            for a
            in ('From:', self.start, 'To:', self.end, distance, directions)
        )
