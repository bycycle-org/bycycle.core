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

    def __str__(self):
        start = self.start
        end = self.end
        directions = []

        for i, direction in enumerate(self.directions, 1):
            turn = direction['turn'].title()
            name = direction['name']
            toward = direction['toward'] or '[unknown]'
            distance = direction['distance']
            directions.append(
                f'{i: >3}. {turn} on {name} toward {toward} -- '
                f'{distance["miles"]:.2f}mi/{distance["kilometers"]:.2f}km')

        directions = '\n'.join(directions) or 'Start and end are the same'

        return f"""\
From: {start.name} 
      {start.geom.y}, {start.geom.x}

  To: {end.name}
      {end.geom.y}, {end.geom.x}

Distance: {self.distance['miles']:.2f}mi/{self.distance['kilometers']:.2f}km

{directions}
"""
