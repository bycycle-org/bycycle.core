"""Lookup service.

The lookup service locates an object (or perhaps objects) based on an
input string, which can have one of the following forms:

    - An object ID (e.g. 'intersection:42')
    - A pair of longitude, latitude coordinates (e.g. '-122,45')
    - An intersection (e.g. '1st & Main'); the cross streets will be
      normalized and then geocoded

These forms will be supported soon:

    - A street address (e.g. '123 Main St); the address will be
      normalized and geocoded
    - A point of interest (e.g. a business or park)

The lookup service will return a :class:`LookupResult` if a matching
object is found. Otherwise it will raise :class:`NoResultError`.

"""
import logging
import re

import mapbox
import mapbox.errors

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from bycycle.core.exc import InputError
from bycycle.core.geometry import DEFAULT_SRID, Point
from bycycle.core.model import LookupResult, Intersection, Street
from bycycle.core.service import AService

from .exc import LookupError, MultipleLookupResultsError, NoResultError


log = logging.getLogger(__name__)


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
            self.match_cross_streets,
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

        result = self.match_via_mapbox(s)
        if result is not None:
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
            return LookupResult(s, obj, geom, obj, obj.name, 'byCycle ID')

    def match_point(self, s):
        if isinstance(s, str):
            try:
                point = Point.from_string(s)
            except ValueError:
                return None

        normalized_point = point
        geom = func.ST_GeomFromText(point.wkt, DEFAULT_SRID)
        distance = func.ST_Distance(
            func.ST_GeogFromWKB(geom),
            func.ST_GeogFromWKB(Intersection.geom))
        distance = distance.label('distance')

        # Distance threshold in meters
        # TODO: Should this be scale-dependent?
        distance_threshold = self.config.get('distance_threshold', 10)

        # Try to get an Intersection first
        q = self.session.query(Intersection, distance)
        q = q.filter(distance < distance_threshold)
        q = q.order_by(distance)
        result = q.first()

        if result is not None:
            closest_object = result.Intersection
            closest_point = closest_object.geom
            name = closest_object.name
        else:
            # Otherwise, get a Street
            distance = func.ST_Distance(geom, Street.geom).label('distance')
            q = self.session.query(Street, distance)
            q = q.filter(
                Street.highway.in_(Street.routable_types) |
                Street.bicycle.in_(Street.bicycle_allowed_types)
            )
            q = q.order_by(distance)
            closest_object = q.first().Street
            # Get point on Street closest to input point
            closest_point = func.ST_ClosestPoint(Street.geom, geom)
            closest_point = closest_point.label('closest_point')
            q = self.session.query(closest_point).select_from(Street)
            q = q.filter_by(id=closest_object.id)
            closest_point = q.scalar()
            closest_point = Point.from_wkb(closest_point)
            name = closest_object.display_name

        return LookupResult(s, normalized_point, closest_point, closest_object, name, 'byCycle point')

    def match_cross_streets(self, s):
        match = CROSS_STREETS_RE.search(s)

        if match is None:
            return None

        data = match.groupdict()

        # Case-insensitive regex operator
        regex_op = Street.name.op('~*')

        q = self.session.query(Intersection)
        q = q.filter(Intersection.streets.any(
            regex_op(r'\m{street}\M'.format(**data)) &
            Street.highway.in_(Street.road_types)
        ))
        q = q.filter(Intersection.streets.any(
            regex_op(r'\m{cross_street}\M'.format(**data)) &
            Street.highway.in_(Street.road_types)
        ))
        q = q.distinct()
        q = q.options(joinedload(Intersection.streets))

        intersections = sorted(q, key=lambda i: i.name)

        if not intersections:
            return None

        results = []

        for intersection in intersections:
            name = intersection.name
            geom = intersection.geom
            results.append(LookupResult(s, name, geom, intersection, name, 'byCycle cross streets'))

        if len(results) == 1:
            return results[0]

        raise MultipleLookupResultsError(choices=results)

    def match_via_mapbox(self, s, relevance_threshold=0.75):
        access_token = self.config.get('mapbox_access_token')
        if not access_token:
            log.warning(
                'LookupService must be configured with a mapbox_access_token to enable geocoding '
                'via Mapbox')
            return None

        bbox = self.config.get('bbox')
        center = self.config.get('center')
        longitude, latitude = center if center else (None, None)

        try:
            # REF: https://docs.mapbox.com/api/search/#geocoding
            geocoder = mapbox.Geocoder(access_token=access_token)

            # XXX: Hard coded country
            # XXX: Hard coded place types
            response = geocoder.forward(
                s,
                bbox=bbox,
                country=['us'],
                lat=latitude,
                lon=longitude,
                limit=3,
                types=['address', 'poi'],
            )
        except mapbox.errors.ValidationError as mapbox_exc:
            raise LookupError('Unable to geocode via Mapbox geocoder', str(mapbox_exc))

        log.info('Mapbox geocoder service response status code: %d', response.status_code)

        data = response.json()

        if response.status_code != 200:
            error_message = data.get('message', 'Unknown Error')
            raise LookupError('Unable to geocode via Mapbox geocoder', error_message)

        all_features = data['features']

        # Filter out less-relevant features
        relevant_features = [f for f in all_features if f['relevance'] > relevance_threshold]

        # Sort by relevance and prominence
        relevant_features = sorted(
            relevant_features, key=lambda f: (f['relevance'], f.get('score', 0)))

        num_features = len(relevant_features)

        if num_features == 0:
            if all_features:
                # Fall back to the most-relevant feature
                relevant_features = [all_features[0]]
                num_features = 1
            else:
                return None

        if num_features == 1:
            result = relevant_features[0]
            return self._mapbox_result_to_lookup_result(s, result)
        else:
            results = tuple(self._mapbox_result_to_lookup_result(s, r) for r in relevant_features)
            raise MultipleLookupResultsError(choices=results)

    def _mapbox_result_to_lookup_result(self, s, result):
        name = result['place_name'].rsplit(', ', 1)[0]  # Remove country
        long, lat = result['center']
        geom = Point(long, lat)
        closest_object = self.match_point(f'{lat},{long}').closest_object
        data = {
            'relevance': result['relevance'],
            'score': result.get('score'),  # Mapbox prominence score
        }
        return LookupResult(s, name, geom, closest_object, name, 'Mapbox', data)


Service = LookupService
