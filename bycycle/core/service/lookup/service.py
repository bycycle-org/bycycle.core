"""Lookup service.

The lookup service locates an object (or perhaps objects) based on an
input string, which can have one of the following forms:

    - An object ID (e.g. 'intersection:42')
    - A pair of longitude, latitude coordinates (e.g. '-122,45')

These forms will be supported soon:

    - A street address (e.g. '123 Main St); the address will be
      normalized and geocoded
    - An intersection (e.g. '1st & Main'); the cross streets will be
      normalized and then geocoded
    - A point of interest (e.g. a business or park)

The lookup service will return a :class:`LookupResult` if a matching
object is found. Otherwise it will return ``None``.

"""
import re

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from bycycle.core.exc import InputError
from bycycle.core.geometry import DEFAULT_SRID, Point
from bycycle.core.model import LookupResult, Intersection, Street
from bycycle.core.service import AService

from .exc import MultipleLookupResultsError, NoResultError


ID_RE = re.compile(r'^(?P<type>[a-z]+):(?P<id>\d+)$')
CROSS_STREETS_RE = re.compile(r'^\s*(?P<street>.+)\s+(?:and|at|&)\s+(?P<cross_street>.+)\s*$')
TYPE_MAP = {
    'intersection': Intersection,
    'street': Street,
}


class LookupService(AService):

    name = 'lookup'

    def query(self, s, point_hint=None):
        matchers = (
            self.match_id,
            self.match_point,
            self.match_address,
            self.match_cross_streets,
            self.match_poi,
        )

        for matcher in matchers:
            result = matcher(s)
            if result is not None:
                return result

        if point_hint:
            result = self.match_point(point_hint)
            result.original_input = s
            result.normalized_input = result.name
            return result

        raise NoResultError(s)

    def is_lat_long(self, point):
        return abs(point.x) <= 180 and abs(point.y) <= 90

    def match_id(self, s):
        match = ID_RE.search(s)
        if match:
            type_ = match.group('type')
            if type_ not in TYPE_MAP:
                raise InputError('Unknown type: %s' % type_)
            type_ = TYPE_MAP[type_]
            obj = self.session.query(type_).get(match.group('id'))
            if obj is None:
                return None
            if isinstance(obj, Intersection):
                geom = obj.geom
            else:
                length = obj.geom.length
                geom = Point(obj.geom.interpolate(length / 2))
            return LookupResult(s, obj, geom, obj, obj.name)

    def match_point(self, s):
        if isinstance(s, str):
            try:
                point = Point.from_string(s)
            except ValueError:
                return None
        normalized_point = point
        if self.is_lat_long(point):
            point = point.reproject()
        geom = func.ST_GeomFromText(point.wkt, DEFAULT_SRID)
        distance = func.ST_Distance(geom, Intersection.geom)
        distance = distance.label('distance')
        # Try to get an Intersection first
        q = self.session.query(Intersection, distance)
        q = q.filter(distance < 5)  # 5 meters (make configurable)
        q = q.order_by(distance)
        result = q.first()
        if result is not None:
            closest_object = result.Intersection
            closest_point = closest_object.geom
        else:
            # Otherwise, get a Street
            distance = func.ST_Distance(geom, Street.geom).label('distance')
            q = self.session.query(Street, distance)
            q = q.order_by(distance)
            closest_object = q.first().Street
            # Get point on Street closest to input point
            closest_point = func.ST_ClosestPoint(Street.geom, geom)
            closest_point = closest_point.label('closest_point')
            q = self.session.query(closest_point).select_from(Street)
            q = q.filter_by(id=closest_object.id)
            closest_point = q.scalar()
            closest_point = Point.from_wkb(closest_point)
        name = closest_object.name
        return LookupResult(s, normalized_point, closest_point, closest_object, name)

    def match_address(self, s):
        return None

    def match_cross_streets(self, s):
        match = CROSS_STREETS_RE.search(s)

        if match is None:
            return None

        data = match.groupdict()

        # Case-insensitive regex operator
        regex_op = Street.name.op('~*')

        q = self.session.query(Intersection)
        q = q.filter(Intersection.streets.any(regex_op(r'\m{street}\M'.format(**data))))
        q = q.filter(Intersection.streets.any(regex_op(r'\m{cross_street}\M'.format(**data))))
        q = q.distinct()
        q = q.options(joinedload(Intersection.streets))

        matches = sorted(q, key=lambda i: i.name)

        if not matches:
            return None

        filtered_matches = []

        for intersection in matches:
            buffer = intersection.geom.buffer(100)
            for f, f_buffer in filtered_matches:
                if buffer.overlaps(f_buffer):
                    break
            else:
                filtered_matches.append((intersection, buffer))

        filtered_matches = [f[0] for f in filtered_matches]

        if len(filtered_matches) == 1:
            intersection = filtered_matches[0]
            name = intersection.name
            geom = intersection.geom
            return LookupResult(s, name, geom, intersection, name)

        raise MultipleLookupResultsError(choices=filtered_matches)

    def match_poi(self, s):
        return None


Service = LookupService
