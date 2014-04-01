from . import Entity


class LookupResult(Entity):

    """Result returned from a :class:`LookupService`.

    Has the following fields:

        - original input string
        - normalized input; this will be the canonical representation
          of the original input string (e.g., if the original was a
          string representing a point, this will be a Point object)
        - location of input
          - If input is an ID, this will be the location of the
            corresponding object
          - If input is a point, this will that point
          - If the input is geocoded, it will be the geocoded point
        - nearest object
        - a normalized address

    """

    def __init__(self, original_input, normalized_input, point, obj, address):
        self.id = '{0.__class__.__name__}:{0.id}'.format(obj).lower()
        self.original_input = original_input
        self.normalized_input = normalized_input
        self.point = point
        self.lat_long = point.lat_long
        self.obj = obj
        self.address = address or '[unknown]'

    def __str__(self):
        return '\n'.join(str(attr) for attr in (self.address, self.lat_long))
