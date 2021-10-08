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
            result; defaults to location as ``'{latitude}, {longitude}``
        attribution (str):
            Attribution for the result (i.e., it's source; e.g., Mapbox)
        data (dict):
            Additional, source-specific data

    """

    def __init__(self, original_input, normalized_input, geom, closest_object, name,
                 attribution=None, data=None):
        self.id = f'{closest_object.__class__.__name__}:{closest_object.id}'.lower()
        self.original_input = original_input
        self.normalized_input = normalized_input
        self.geom = geom
        self.closest_object = closest_object
        self.name = name or f'{geom.y:.5f}, {geom.x:.5f}'
        self.attribution = attribution
        self.data = data

    def __str__(self):
        return '\n'.join(str(attr) for attr in (self.name, self.geom))

    def __eq__(self, other):
        return self.id == other.id
