import math
from math import sin, cos, acos, atan2, radians, degrees


earth_radius = 3959
equator_circumference = 24902
miles_per_degree_at_equator = equator_circumference/360


def getCenterOfBounds(bounds):
    sw = bounds['sw'];
    ne = bounds['ne'];
    return {'x': (sw['x'] + ne['x']) / 2.0, 'y': (sw['y'] + ne['y']) / 2.0};


def getDistanceBetweenTwoPointsOnEarth(xy_a=None, xy_b=None,
                                       x_a=None, y_a=None,
                                       x_b=None, y_b=None):
    if xy_a and xy_b:
        x_a = xy_a.x
        y_a = xy_a.y
        x_b = xy_b.x
        y_b = xy_b.y
    if x_a == x_b and y_a == y_b:
        return 0
    return earth_radius * \
           acos(cos(radians(y_a)) * \
                cos(radians(y_b)) * \
                cos(radians(x_b-x_a)) + \
                sin(radians(y_a)) * \
                sin(radians(y_b)))


def getLengthOfLineString(linestring,
                          distanceFunc=getDistanceBetweenTwoPointsOnEarth):
    length = 0
    for i, p in enumerate(linestring[:-1]):
        length += distanceFunc(p, linestring[i+1])
    return length


def getDistanceBetweenTwoPoints(p, q):
    x1, y1 = p.x, p.y
    x2, y2 = q.x, q.y
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    length = math.sqrt(math.pow(dx, 2) + math.pow(dy, 2))
    return length


def getDistanceBetweenTwoLatitudes(y_a, y_b):
    return miles_per_degree_at_equator * abs(y_b - y_a)


def getDistanceBetweenTwoLongitudes(y, x_a, x_b):
    return cos(radians(y)) * miles_per_degree_at_equator * abs(x_b - x_a)


def getBearingGivenStartAndEndPoints(p, q):
    dx = q.x - p.x
    dy = q.y - p.y
    deg = degrees(atan2(dx, dy))
    while deg < 0:
        deg += 360
    return deg


def getInterpolatedXY(linestring, length, distance_from_start):
    """
    @param linestring A list of Points (having x and y attributes)
    @param length The length of the linestring (in any convenient units)
    @param distance_from_start How far the point to interpolate is from the
           start of the linestring (in same units as length)

    @return An interpolated Point

    """
    ls_len = len(linestring)
    if type(linestring) != type([]) or ls_len < 2: return None
    length = length or .000000000000001
    pct_from_start = distance_from_start / length
    pct_from_end = 1.0 - pct_from_start

    if ls_len == 2:
        fxy, txy = linestring[0], linestring[-1]
        x = fxy.x * pct_from_end + txy.x * pct_from_start
        y = fxy.y * pct_from_end + txy.y * pct_from_start
    else:
        # TODO: don't assume all the line string piece are equal length
        pieces = ls_len - 1 * 1.0
        pct_per_piece = (length / pieces) / length

        try: p = pct_from_start / pct_per_piece
        except ZeroDivisionError:
            fxy, txy = linestring[0], linestring[-1]
            x = fxy.x*pct_from_end + txy.x*pct_from_start
            y = fxy.y*pct_from_end + txy.y*pct_from_start
        else:
            import math
            floor_p = int(math.floor(p))
            ceiling_p = int(math.ceil(p))
            if floor_p == ceiling_p:
                xy = linestring[floor_p]
                x, y = xy.x, xy.y
            else:
                ps = p - floor_p
                pe = ceiling_p - p
                try:
                    fxy, txy = linestring[floor_p], linestring[ceiling_p]
                except IndexError:
                    xy = linestring[floor_p]
                    x, y = xy.x, xy.y
                else:
                    x = fxy.x * pe + txy.x * ps
                    y = fxy.y * pe + txy.y * ps

    return Point(x=x, y=y)


def importWktGeometry(geom):
    """Return a simple Python object for the given WKT Geometry string.

    POINT(X Y)
    LINESTRING(X Y,X Y,X Y)

    """
    geom_type, wkt_data = geom.split('(', 1)
    geom_type = geom_type.strip().upper()
    wkt_data = wkt_data[:-1] # strip trailing )
    if geom_type == 'LINESTRING':
        wkt_data = wkt_data.split(',')   # list of 'X Y'
        wkt_data = [d.split() for d in wkt_data] # list of [X, Y]
        linestring = [Point(x=d[0], y=d[1]) for d in wkt_data]
        return linestring
    elif geom_type == 'POINT':
        x, y = wkt_data.split()
        return Point(x=x, y=y)
    else:
        raise TypeError('Unsupported WKT geometry type: "%s"' % geom_type)


def importWktGeometries(geoms, geom_type):
    """Return list of simple Python objects for list of WKT Geometries.

    This function is intended to be used instead of looping over a bunch of WKT
    geometries and making a kabillion calls to importWktGeometry(), which is
    why DRY is violated here.

    """
    lGeoms = []
    geom_type = geom_type.strip().upper()
    if geom_type == 'POINT':
        for p in geoms:
            # TODO: some type/value checking
            x, y = p.split('(', 1)[1][:-1].split()
            lGeoms.append(Point(x=x, y=y))
        return lGeoms
    else:
        raise TypeError('Unsupported WKT geometry type: "%s"' % geom_type)




class Point(object):
    """A very simple Point class."""
    def __init__(self, x_y=None, x=None, y=None):
        """Create a new Point from the supplied 2-tuple or string.

        @param x_y Either a 2-tuple of floats (or string representations of
                   floats), a string that will eval as such a tuple, or
                   another Point
        @param x The x-coordinate of the point
        @param y The y-coordinate of the point

        If x and y are passed, they will be preferred over x_y.
        Clone a Point by passing it as the x_y arg to a new Point.

        """
        err = 'Bad value(s) for Point: "%s", "%s"'
        if x is not None and y is not None:
            # x and y were passed; prefer them over x_y
            try:
                self.x, self.y = float(x), float(y)
            except (ValueError, TypeError):
                raise ValueError(err % (x, y))
        elif x_y is not None:
            # x_y was passed and at least one of x and y wasn't
            try:
                # See if x_y is another point (or object with x and y attrs)
                self.x, self.y = float(x_y.x), float(x_y.y)
            except AttributeError:
                if isinstance(x_y, tuple):
                    # See if x_y is a 2-tuple (either of floats or string
                    # reprensentations of floats)...
                    try:
                        self.x, self.y = float(x_y[0]), float(x_y[1])
                    except IndexError:
                        length = len(x_y)
                        if length == 0:
                            raise ValueError('Missing x and y values')
                        elif length == 1:
                            raise ValueError('Missing y value (x: "%s")' %
                                             x_y[0])
                    except (ValueError, TypeError):
                        raise ValueError(err % (tmp_x_y.x, tmp_x_y.y))
                elif isinstance(x_y, basestring):
                    try:
                        # See if x_y is string that will evaluate as 2-tuple
                        tmp_x_y = eval(x_y)
                    except:
                        # Last effort: See if x_y is a point given as a
                        # kwargs-style string or a WKT POINT
                        # Both will raise a ValueError if they can't parse
                        # the string
                        try:
                            self.x, self.y = self._importKwargsPoint(x_y)
                        except (TypeError, ValueError):
                            point = importWktGeometry(x_y)
                            self.x, self.y = point.x, point.y
                    else:
                        try:
                            self.x = float(tmp_x_y[0])
                            self.y = float(tmp_x_y[1])
                        except (ValueError, TypeError):
                            raise ValueError(err % (tmp_x_y.x, tmp_x_y.y))
            except (ValueError, TypeError):
                raise ValueError(err % (x_y.x, x_y.y))
        else:
            # No args passed; create a default empty Point
            self.x = None
            self.y = None


    def _importKwargsPoint(self, x_y):
        """A kwargs point is a str with x & y specified like keyword args.

        @param x_y String like 'x=-123, y=45'
               x can be one of x, lng, lon, long, longitude
               y can be one of y, y, latitude
               [When x or y is not in the list, the positional value will be
                used]
               = can be one of =, :
               , can be one of [comma], [space]
        @return x, y Floats
        @raise ValueError or TypeError on bad input

        """
        err = 'Could not parse x and y from "%s"' % x_y

        try:
            x, y = x_y.split(',')
        except ValueError:
            x, y = x_y.split(' ')

        try:
            x_label, x = x.split('=')
        except ValueError:
            x_label, x = x.split(':')

        try:
            y_label, y = y.split('=')
        except ValueError:
            y_label, y = y.split(':')

        try:
            if x_label in ('x', 'lng', 'lon', 'long', 'longitude'):
                x = float(x)
            elif x_label in ('y', 'lat', 'latitude'):
                y = float(x)

            if y_label in ('x', 'lng', 'lon', 'long', 'longitude'):
                x = float(y)
            elif y_label in ('y', 'lat', 'latitude'):
                y = float(y)
        except TypeError:
            raise ValueError(err)

        try:
            return x, y
        except NameError:
            raise ValueError(err)


    def __str__(self):
        return 'POINT(%.6f %.6f)' % (self.x, self.y)


    def __repr__(self):
        return "{'x': %f, 'y': %f}" % (self.x, self.y)

