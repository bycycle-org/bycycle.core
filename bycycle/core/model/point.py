import re


class InitCoordinatesException(Exception):
    def __init__(self, msg):
        self.msg = msg


class Point(object):
    """Simple point. Currently supports only X and Y (and not Z)."""

    def __init__(self, point=None, x=None, y=None, z=None):
        """Coords can be given via ``point`` OR ``x`` AND ``y`` AND ``z``.

        ``point`` `string` | `list` | `tuple` | `object` | `dict`
            - A WKT geometry string (POINT(-123 45))
            - A sequence of floats (or string representations of floats)
            - A keyword args style string (x=-123, y=45)
            - An object with x, y, z attributes
            - A dict with x, y, and z keys
            - A string that will eval as an object, dict, tuple, or list

        ``x`` -- X coordinate
        ``y`` -- Y coordinate
        ``z`` -- Z coordinate

        Use ``x`` and ``y`` if both are given. Otherwise, get coordinates from
        ``point``. Currently, the Z coordinate is not supported.

        return `tuple` -- floats X and Y

        TODO: Support Z coordinate

        """
        self.x, self.y, self.z = self._initCoordinates(point, x, y, z)

    def _initCoordinates(self, point, x, y, z):
        """Get x, y, and z coordinates.

        See __init__ for parameter details.

        ``point``
        ``x``
        ``y``
        ``z``

        return `tuple` -- X, Y, and Z coordinates. For now, Z is always None.

        raise ValueError
            - Coordinates cannot be parsed
            - Neither ``point`` nor both of ``x`` and ``y`` are given

        """
        if x is not None and y is not None:
            # ``x`` and ``y`` were passed; prefer them over ``point``.
            try:
                x, y = [float(v) for v in (x, y)]
            except (ValueError, TypeError):
                err = 'X and Y values must be floats. X: "%s", Y: "%s".'
                raise ValueError(err % (x, y))
            else:
                return x, y, None
        elif point is not None:
            # ``point`` was passed and at least one of ``x`` and ``y`` wasn't
            # Try a bunch of different methods of parsing coordinates from
            # ``point``
            methods = (
                self._initCoordinatesFromObject,
                self._initCoordinatesFromDict,
                self._initCoordinatesFromEval,
                self._initCoordinatesFromKwargsString,
                self._initCoordinatesFromWKTString,
                self._initCoordinatesFromSequence,
            )
            for meth in methods:
                try:
                    x, y = meth(point)
                except InitCoordinatesException:
                    # Catch any "expected" exceptions--the _initCoordinates*
                    # methods catch various expected exceptions and raise
                    # this.
                    pass
                else:
                    try:
                        x, y = [float(v) for v in (x, y)]
                    except (ValueError, TypeError):
                        pass
                    else:
                        return x, y, None
            raise ValueError(
                'Could not initialize coordinates from "%s".' % str(point)
            )
        else:
            raise ValueError(
                'No arguments passed to initialize coordinates from. Pass '
                'either point OR x and y.'
            )

    def _initCoordinatesFromSequence(self, s):
        try:
            return s[0], s[1]
        except IndexError:
            length = len(point)
            if length == 0:
                raise InitCoordinatesException('Missing x and y values.')
            elif length == 1:
                raise InitCoordinatesException(
                    'Missing y value (x: "%s").' % s[0]
                )

    def _initCoordinatesFromEval(self, s):
        try:
            eval_point = eval(s)
        except:
            raise InitCoordinatesException(
                '"%s" could not be evaled.' % str(s)
            )
        else:
            # Call recursively because we don't know what
            # point evaled as.
            x, y, z = self._initCoordinates(eval_point, None, None, None)
            return x, y

    def _initCoordinatesFromWKTString(self, wkt):
        if isinstance(wkt, str):
            wkt = wkt.strip().upper()
            if wkt.startswith('POINT'):
                wkt = wkt[5:].strip()
                if wkt.startswith('('):
                    wkt = wkt.lstrip('(')
                    if wkt.endswith(')'):
                        wkt = wkt.rstrip(')')
                        return wkt.split()
        raise InitCoordinatesException(
            '"%s" does not appear to be a WKT point.' % str(wkt))

    def _initCoordinatesFromObject(self, obj):
        try:
            return obj.x, obj.y
        except AttributeError:
            raise InitCoordinatesException(
                '"%s" does not have both x and y attributes.' % str(obj)
            )

    def _initCoordinatesFromDict(self, d):
        try:
            return d['x'], d['y']
        except KeyError:
            raise InitCoordinatesException(
                '"%s" does not contain both x and y keys.' % str(d)
            )
        except TypeError:
            raise InitCoordinatesException(
                '"%s" is not a dict.' % str(d)
            )

    def _initCoordinatesFromKwargsString(self, point):
        """A kwargs point is a str with x & y specified like keyword args.

        ``point`` `string` -- A string of this form: "x=-123, y=45"
            - x can be one of x, lng, lon, long, longitude
            - y can be one of y, lat, latitude
            - When x or y is not in the list, the first value will be used as
              the x value and the second as the y value
            - = can be one of [equal sign] or [colon]
            - , can be one of [comma] or [space]

        return `tuple` -- (float(x), float(y))

        raise `ValueError`

        """
        err = '"%s" is not a keyword-args style string.' % str(point)

        if not isinstance(point, str):
            raise InitCoordinatesException(err)

        point = point.strip()

        pattern = (
            r'(?P<x_label>[a-z]+)\s*(=|:)\s*(?P<x>-?\d+(?:\.\d+)?)'
            r'\s*,?\s*'
            r'(?P<y_label>[a-z]+)\s*(=|:)\s*(?P<y>-?\d+(?:\.\d+)?)'
        )

        x_labels = ('x', 'lng', 'lon', 'long', 'longitude')
        y_labels = ('y', 'lat', 'latitude')

        match = re.match(pattern, point)
        if match:
            x_label = match.group('x_label')
            x = float(match.group('x'))
            y_label = match.group('y_label')
            y = float(match.group('y'))
            if x_label in y_labels and y_label in x_labels:
                x, y = y, x
            return x, y

        raise InitCoordinatesException(err)

    def __str__(self):
        """Return a WKT string for this point."""
        return 'POINT (%.6f %.6f)' % (self.x, self.y)

    def __repr__(self):
        return (
            "{'x': %.6f, 'y': %.6f, 'z': %.6f}" %
            (self.x, self.y, self.z or 0.0)
        )
