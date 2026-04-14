"""Lookup service.

The lookup service locates an object (or perhaps objects) based on an
input string, which can have one of the following forms:

    - An object ID (e.g. "intersection:42")
    - A pair of longitude, latitude coordinates (e.g. "-122,45")
    - An intersection (e.g. "1st & Main"); the cross streets will be
      normalized and then geocoded

These forms will be supported soon:

    - A street address (e.g. "123 Main St"); the address will be
      normalized and geocoded
    - A point of interest (e.g. a business or park)

The lookup service will return a :class:`LookupResult` if a matching
object is found. Otherwise, it will raise :class:`NoResultError`.

"""

import logging
import re

import mapbox
import mapbox.errors
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Q
from shapely.geometry import Point

from bycycle.core.exc import InputError
from bycycle.core.geometry import as_geos, point_from_string
from bycycle.core.models import Intersection, LookupResult, Street
from bycycle.core.services import AService

from .exc import LookupError, MultipleLookupResultsError, NoResultError

log = logging.getLogger(__name__)

ID_RE = re.compile(r"^(?P<type>[a-z]+):(?P<id>\d+)$")
CROSS_STREETS_RE = re.compile(
    r"^\s*(?P<street>.+)\s+(?:and|at|&)\s+(?P<cross_street>.+)\s*$"
)
TYPE_MAP = {
    "intersection": Intersection,
    "street": Street,
}


class LookupService(AService):
    name = "lookup"

    center: tuple[float, float] | None
    bbox: tuple[float, float, float, float] | None
    distance_threshold: int  # meters
    mapbox_access_token: str | None

    def __init__(
        self,
        center: tuple[float, float] = None,
        bbox: tuple[float, float, float, float] = None,
        distance_threshold: int = 10,
        mapbox_access_token: str | None = None,
    ) -> None:
        self.center = center
        self.bbox = bbox
        self.distance_threshold = distance_threshold
        self.mapbox_access_token = mapbox_access_token

    def query(self, query: str, point_hint: str | None = None) -> LookupResult | None:
        """Query this service."""
        result = (
            self.match_id(query)
            or self.match_point(query)
            or self.match_cross_streets(query)
        )

        if result is not None:
            return result

        if point_hint:
            result = self.match_point(point_hint)
            result.original_input = query
            result.normalized_input = result.name
            return result

        if result := self.match_via_mapbox(query):
            return result

        raise NoResultError(query)

    def is_lat_long(self, point) -> bool:
        return abs(point.x) <= 180 and abs(point.y) <= 90

    def match_id(self, id_: str) -> LookupResult | None:
        match = ID_RE.search(id_)
        if not match:
            return None
        type_ = match.group("type")
        id_ = match.group("id")
        if type_ not in TYPE_MAP:
            raise InputError("Unknown type: %s" % type_)
        type_ = TYPE_MAP[type_]
        obj = type_.objects.get(id_)
        if obj is None:
            return None
        if isinstance(obj, Intersection):
            geom = obj.geom
        else:
            length = obj.geom.length
            geom = Point(obj.geom.interpolate(length / 2))
        return LookupResult(id_, obj, geom, obj, obj.name, "byCycle ID")

    def match_point(self, point: str | Point) -> LookupResult | None:
        """Get intersection or street closest to point."""
        if isinstance(point, str):
            try:
                point = point_from_string(point)
            except ValueError:
                return None
            else:
                if point is None:
                    return None

        geos_point = as_geos(point)

        # Distance threshold in meters
        distance_threshold = D(m=self.distance_threshold)

        # Try to get an Intersection first
        q = Intersection.objects.filter(
            geom__distance_lt=(geos_point, distance_threshold)
        )
        q = q.annotate(distance=Distance("geom", geos_point))
        q = q.order_by("distance")
        closest_object = q.first()

        if closest_object is not None:
            closest_point = closest_object.geom
            name = closest_object.name
        else:
            # Otherwise, get a Street
            q = Street.objects.filter(
                Q(highway__in=Street.routable_types)
                | Q(bicycle__in=Street.bicycle_allowed_types)
            )
            q = q.annotate(distance=Distance("geom", geos_point))
            q = q.order_by("distance")
            closest_object = q.first()

            # Get point on Street closest to input point
            points = [Point(p) for p in closest_object.geom]
            closest_point = min(points, key=lambda p: point.distance(p))

            name = closest_object.display_name

        return LookupResult(
            point, point, closest_point, closest_object, name, "byCycle point"
        )

    def match_cross_streets(self, cross_streets: str) -> LookupResult | None:
        match = CROSS_STREETS_RE.search(cross_streets)

        if match is None:
            return None

        data = match.groupdict()
        street = data["street"]
        cross_street = data["cross_street"]

        q = Intersection.objects.distinct()
        q = q.prefetch_related("start_streets", "end_streets")
        q = q.filter(
            start_streets__highway__in=Street.road_types,
            end_streets__highway__in=Street.road_types,
        )
        q = q.filter(
            (
                Q(start_streets__name__iregex=street)
                & Q(end_streets__name__iregex=cross_street)
            )
            | (
                Q(start_streets__name__iregex=cross_street)
                & Q(end_streets__name__iregex=street)
            )
        )

        intersections = sorted(q, key=lambda i: i.name)

        results = []
        for intersection in intersections:
            name = intersection.name
            geom = intersection.geom
            results.append(
                LookupResult(
                    cross_streets,
                    name,
                    geom,
                    intersection,
                    name,
                    "byCycle cross streets",
                )
            )

        match len(results):
            case 0:
                return None
            case 1:
                return results[0]
            case _:
                raise MultipleLookupResultsError(choices=results)

    def match_via_mapbox(self, s, relevance_threshold=0.75) -> LookupResult | None:
        access_token = self.mapbox_access_token

        if not access_token:
            return None

        bbox = self.bbox
        center = self.center
        longitude, latitude = center if center else (None, None)

        try:
            # REF: https://docs.mapbox.com/api/search/#geocoding
            geocoder = mapbox.Geocoder(access_token=access_token)

            # XXX: Hard coded country
            # XXX: Hard coded place types
            response = geocoder.forward(
                s,
                bbox=bbox,
                country=["us"],
                lat=latitude,
                lon=longitude,
                limit=3,
                types=["address", "poi"],
            )
        except mapbox.errors.ValidationError as mapbox_exc:
            raise LookupError("Unable to geocode via Mapbox geocoder", str(mapbox_exc))

        log.info(
            "Mapbox geocoder service response status code: %d", response.status_code
        )

        data = response.json()

        if response.status_code != 200:
            error_message = data.get("message", "Unknown Error")
            raise LookupError("Unable to geocode via Mapbox geocoder", error_message)

        all_features = data["features"]

        # Filter out less-relevant features
        relevant_features = [
            f for f in all_features if f["relevance"] > relevance_threshold
        ]

        # Sort by relevance and prominence
        relevant_features = sorted(
            relevant_features, key=lambda f: (f["relevance"], f.get("score", 0))
        )

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
            results = tuple(
                self._mapbox_result_to_lookup_result(s, r) for r in relevant_features
            )
            raise MultipleLookupResultsError(choices=results)

    def _mapbox_result_to_lookup_result(self, s, result):
        name = result["place_name"].rsplit(", ", 1)[0]  # Remove country
        longitude, latitude = result["center"]
        geom = Point(longitude, latitude)
        closest_object = self.match_point(f"{latitude},{longitude}").closest_object
        data = {
            "relevance": result["relevance"],
            "score": result.get("score"),  # Mapbox prominence score
        }
        return LookupResult(s, name, geom, closest_object, name, "Mapbox", data)


Service = LookupService
