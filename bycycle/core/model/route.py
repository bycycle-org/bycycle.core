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
        distance = self.distance

        directions = []

        direction_template = (
            '{i: >3}. {turn} on {name} toward {toward} -- '
            '{distance[miles]:.2f}mi/{distance[kilometers]:.2f}km'
        )

        for i, direction in enumerate(self.directions, 1):
            turn = direction['turn'].title()
            name = direction['display_name']
            toward = direction['toward'] or '[unknown]'
            distance = direction['distance']
            directions.append(direction_template.format_map(locals()))

        directions = '\n'.join(directions) or 'Start and end are the same'

        return """\
From: {start.name} 
      {start.geom.lat_long}

  To: {end.name}
      {end.geom.lat_long}

Distance: {distance[miles]:.2f}mi/{distance[kilometers]:.2f}km

{directions}
""".format_map(locals())
