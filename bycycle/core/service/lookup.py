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

from sqlalchemy.sql import func

from bycycle.core.exc import NotFoundError
from bycycle.core.geometry import DEFAULT_SRID, Point
from bycycle.core.model import LookupResult, Intersection, Street

from .base import AService


ID_RE = re.compile(r'(?P<type>[a-z]+):(?P<id>\d+)')
TYPE_MAP = {
    'intersection': Intersection,
    'street': Street,
}


class LookupService(AService):

    name = 'lookup'

    def query(self, s, id_hint=None, point_hint=None):
        hint_result = preferred_obj = preferred_point = None

        if id_hint:
            hint_result = self.match_id(id_hint)
            if hint_result is not None:
                preferred_obj = hint_result.obj
                preferred_point = hint_result.point
            else:
                # TODO: Log that ID hint wasn't found or raise exc?
                pass

        if point_hint:
            preferred_point = Point.from_string(point_hint)
            preferred_point.reproject()
            if hint_result is None:
                hint_result = self.match_point(point_hint)

        # TODO: Return early if s == id_hint or s == point_hint?

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
                if preferred_obj is not None:
                    result.obj = preferred_obj
                if preferred_point is not None:
                    result.point = preferred_point
                return result

        # Fallback result
        if hint_result is not None:
            return hint_result

        raise NotFoundError('Could not find {}'.format(s))

    def match_id(self, s):
        match = ID_RE.match(s)
        if match:
            type_ = match.group('type')
            type_ = TYPE_MAP[type_]
            id = int(match.group('id'))
            obj = self.session.query(type_).get(id)
            if isinstance(obj, Intersection):
                point = obj.geom
            else:
                point = Point(obj.geom.centroid)
            address = obj.name
            return LookupResult(s, obj, point, obj, address)

    def match_point(self, s):
        try:
            point = Point.from_string(s)
        except ValueError:
            return None
        else:
            normalized_point = point
            point = point.reproject()
            geom = func.ST_GeomFromText(point.wkt, DEFAULT_SRID)
            distance = func.ST_Distance(geom, Intersection.geom)
            distance = distance.label('distance')
            # Try to get a Intersection first
            q = self.session.query(Intersection, distance)
            q = q.filter(distance < 5)  # 5 meters (make configurable)
            q = q.order_by(distance)
            result = q.first()
            if result is not None:
                obj = result.Intersection
                closest_point = obj.geom
            else:
                # Otherwise, get a Street
                distance = func.ST_Distance(geom, Street.geom).label('distance')
                q = self.session.query(Street, distance)
                q = q.order_by(distance)
                obj = q.first().Street
                # Get point on Street closest to input point
                closest_point = func.ST_ClosestPoint(Street.geom, geom)
                closest_point = closest_point.label('closest_point')
                q = self.session.query(closest_point).select_from(Street)
                q = q.filter_by(id=obj.id)
                closest_point = q.scalar()
                closest_point = Point.from_wkb(closest_point)
            address = obj.name
            return LookupResult(
                s, normalized_point, closest_point, obj, address)

    def match_address(self, s):
        return None

    def match_cross_streets(self, s):
        return None

    def match_poi(self, s):
        return None


Service = LookupService
