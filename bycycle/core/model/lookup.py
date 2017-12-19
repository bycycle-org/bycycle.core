from . import Entity


class LookupResult(Entity):

    """Result returned from :class:`LookupService`.

    Args:
        original_input (str):
            The original input string
        normalized_input (object):
            The canonical representation of the original input string
            (e.g., if the original was a string representing a point,
            this will be a Point object)
        geom (Point):
            Location of result:
                - If input is an ID, this will be the geom of the
                  corresponding object
                - If input is a point, this will be that point
                - If the input is geocoded, it will be the geocoded
                  point
        closest_object (object):
            Nearest object (intersection or street)
        name (str):
            Address, cross streets, or whatever is appropriate for the
            result

    """

    def __init__(self, original_input, normalized_input, geom, closest_object, name):
        self.id = '{0.__class__.__name__}:{0.id}'.format(closest_object).lower()
        self.original_input = original_input
        self.normalized_input = normalized_input
        self.geom = geom
        self.closest_object = closest_object
        self.name = name or '{lat_long.x:.5f}, {lat_long.y:.5f}'.format(lat_long=geom.lat_long)

    def __str__(self):
        return '\n'.join(str(attr) for attr in (self.name, self.geom.lat_long))
