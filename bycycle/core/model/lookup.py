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
                - If input is an ID, this will be a point derived from
                  the corresponding object. E.g., if it's the ID of an
                  intersection, this will be the point the intersection
                  is at; if it's the ID of a street, it will be the
                  midpoint of the street.
                - If input is a point, this will be that point.
                - If the input is geocoded, it will be the geocoded
                  point.
        closest_object (object):
            Nearest object (intersection or street)
        name (str):
            Address, cross streets, or whatever is appropriate for the
            result

    """

    def __init__(self, original_input, normalized_input, geom, closest_object, name,
                 attribution=None):
        self.id = '{0.__class__.__name__}:{0.id}'.format(closest_object).lower()
        self.original_input = original_input
        self.normalized_input = normalized_input
        self.geom = geom
        self.closest_object = closest_object
        self.name = name or '{lat_long.x:.5f}, {lat_long.y:.5f}'.format(lat_long=geom.lat_long)
        self.attribution = attribution

    def __str__(self):
        return '\n'.join(str(attr) for attr in (self.name, self.geom.lat_long))
