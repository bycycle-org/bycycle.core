import logging
from itertools import chain
from math import atan2, degrees

from dijkstar.server.client import Client, ClientError

from sqlalchemy.orm import joinedload

from bycycle.core.exc import InputError
from bycycle.core.geometry import length_in_meters, split_line, trim_line, LineString, Point
from bycycle.core.model import Intersection, LookupResult, Route, Street
from bycycle.core.service import AService, LookupService
from bycycle.core.service.lookup import MultipleLookupResultsError

from .exc import MultipleRouteLookupResultsError, NoRouteError


log = logging.getLogger(__name__)


class RouteService(AService):

    """Route-finding Service."""

    name = 'route'

    def query(self, q, points=None):
        waypoints = self.get_waypoints(q, points)
        starts = waypoints[:-1]
        ends = waypoints[1:]
        routes = []
        for start, end in zip(starts, ends):
            if start.geom == end.geom:
                coords = start.geom.coords[0]
                route = Route(start, end, [], LineString([coords, coords]), self.distance_dict(0))
            else:
                path = self.find_path(start, end)
                directions, linestring, distance = self.make_directions(*path)
                route = Route(start, end, directions, linestring, distance)
            routes.append(route)
        return routes[0] if len(routes) == 1 else routes

    def get_waypoints(self, q, points=None):
        errors = []
        waypoints = [w.strip() for w in q]
        num_waypoints = len(waypoints)
        points = points or [None] * num_waypoints
        if num_waypoints != len(points):
            errors.append('Number of points does not match number of waypoints')
        if num_waypoints == 0:
            errors.append('Please enter starting point and destination')
        if num_waypoints == 1:
            errors.append('Please enter a destination')
        else:
            if num_waypoints == 2:
                if not waypoints[0]:
                    errors.append('Please enter a starting point')
                if not waypoints[-1]:
                    errors.append('Please enter a destination')
            else:
                for w in waypoints:
                    if not w:
                        errors.append('Destinations cannot be blank')
                        break
        if errors:
            raise InputError(errors)
        lookup_service = LookupService(self.session, **self.config)
        results = []
        raise_multi = False
        for w, point_hint in zip(waypoints, points):
            try:
                result = lookup_service.query(w, point_hint)
            except MultipleLookupResultsError as exc:
                raise_multi = True
                results.append(exc.choices)
            else:
                results.append(result)
        if raise_multi:
            raise MultipleRouteLookupResultsError(choices=results)
        return results

    def find_path(self, start_result: LookupResult, end_result: LookupResult,
                  cost_func: str = None, heuristic_func: str = None):
        client = Client()

        start = start_result.closest_object
        end = end_result.closest_object
        annex_edges = []
        split_ways = {}

        add_between = isinstance(start, Street) and isinstance(end, Street) and start.id == end.id

        if isinstance(start, Street):
            start, *start_ways, start_edges = self.split_way(start, start_result.geom, -1, -1, -2)
            annex_edges.extend(start_edges)
            split_ways.update({w.id: w for w in start_ways})

        if isinstance(end, Street):
            end, *end_ways, end_edges = self.split_way(end, end_result.geom, -2, -3, -4)
            annex_edges.extend(end_edges)
            split_ways.update({w.id: w for w in end_ways})

        if add_between:
            obj = start_result.closest_object
            geom = trim_line(obj.geom, start.geom, end.geom)

            d1 = obj.geom.project(start.geom)
            d2 = obj.geom.project(end.geom)

            if d1 <= d2:
                start_node, end_node = start, end
            else:
                start_node, end_node = end, start

            if obj.base_cost is None:
                base_cost = None
            else:
                fraction = length_in_meters(geom) / obj.meters
                base_cost = obj.base_cost * fraction

            way = obj.clone(
                id=-3,
                geom=geom,
                start_node_id=start_node.id,
                start_node=start_node,
                end_node_id=end_node.id,
                end_node=end_node,
                base_cost=base_cost)

            way_attrs = (way.id, base_cost, way.name)
            annex_edges.append((start_node.id, end_node.id, way_attrs))
            if not way.oneway_bicycle:
                annex_edges.append((end_node.id, start_node.id, way_attrs))

            split_ways[way.id] = way

        try:
            result = client.find_path(
                start.id,
                end.id,
                annex_edges=annex_edges,
                cost_func=cost_func,
                heuristic_func=heuristic_func,
                fields=('nodes', 'edges')
            )
        except ClientError as exc:
            status_code = exc.response.status_code
            data = exc.response.json()
            detail = data['detail']
            if status_code == 400:
                raise InputError(detail)
            if status_code == 404:
                raise NoRouteError(start_result, end_result)
            raise

        nodes = result['nodes']
        edges = [edge[0] for edge in result['edges']]

        assert nodes[0] == start.id, f'Expected route start node ID: {start.id}; got {nodes[0]}'
        assert nodes[-1] == end.id, f'Expected route end node ID: {start.id}; got {nodes[-1]}'

        return nodes, edges, split_ways

    def split_way(self, way, point, node_id, way1_id, way2_id):
        start_node_id, end_node_id = way.start_node.id, way.end_node.id

        way1_line, way2_line = split_line(way.geom, point)
        shared_node = Intersection(id=node_id, geom=point)

        if way.base_cost is None:
            way1_base_cost = None
            way2_base_cost = None
        else:
            way1_fraction = length_in_meters(way1_line) / way.meters
            way1_base_cost = way.base_cost * way1_fraction
            way2_fraction = length_in_meters(way2_line) / way.meters
            way2_base_cost = way.base_cost * way2_fraction

        way1 = way.clone(
            id=way1_id,
            geom=way1_line,
            end_node_id=shared_node.id,
            end_node=shared_node,
            base_cost=way1_base_cost)

        way2 = way.clone(
            id=way2_id,
            geom=way2_line,
            start_node_id=shared_node.id,
            start_node=shared_node,
            base_cost=way2_base_cost)

        way1_attrs = (way1.id, way1.base_cost, way1.name)
        way2_attrs = (way2.id, way2.base_cost, way2.name)

        # Add edge from start node to split node and from split node to
        # end node.
        annex_edges = [
            (start_node_id, node_id, way1_attrs),
            (node_id, end_node_id, way2_attrs),
        ]

        # If end node => start node, add edge from end node to split
        # node and from split node to start node.
        if not way.oneway_bicycle:
            annex_edges.extend([
                (end_node_id, node_id, way2_attrs),
                (node_id, start_node_id, way1_attrs),
            ])

        return shared_node, way1, way2, annex_edges

    def make_directions(self, node_ids, edge_ids, split_edges):
        """Process the shortest path into a nice list of directions.

        ``node_ids``
            The IDs of the nodes on the route

        ``edges_ids``
            The IDs of the edges on the route

        ``split_edges``
            Temporary edges formed by splitting an existing edge when the
            start and/or end of a route is within an edge (e.g., for an
            address like "123 Main St")

        return
            * A list of directions. Each direction has the following form::

              {
                  'turn': 'left',
                  'name': 'SE Stark St',
                  'type': 'residential',
                  'toward': 'SE 45th Ave',
                  'distance': {
                       'meters': 80.0,
                       'kilometers': 0.08,
                       'feet': 264.0,
                       'miles': 0.05,
                   },
                  'point': (-122.5, 45.5),
                  'edge_ids': [1, 2, 3, 4],
               }

            * A linestring, which is a list of x, y coords:

              [(x, y), ...]

            * A `dict` of total distances in units of meters,
              kilometers, feet, and miles:

              {
                  'meters': 1110.0,
                  'kilometers': 1.11,
                  'feet': 5487.0,
                  'miles': 1.04,
              }

        """
        edges = []

        synthetic_start_edge = edge_ids[0] < 0
        synthetic_end_edge = len(edge_ids) > 1 and edge_ids[-1] < 0

        if synthetic_start_edge:
            edges.append(split_edges[edge_ids[0]])

        i = 1 if synthetic_start_edge else None
        j = -1 if synthetic_end_edge else None
        filter_ids = edge_ids[i:j] if i or j else edge_ids
        if filter_ids:
            q = self.session.query(Street).filter(Street.id.in_(filter_ids))
            q = q.options(joinedload(Street.start_node))
            q = q.options(joinedload(Street.end_node))
            edge_map = {edge.id: edge for edge in q}
            edges.extend(edge_map[edge_id] for edge_id in filter_ids)

        if synthetic_end_edge:
            edges.append(split_edges[edge_ids[-1]])

        directions = []
        stretches = []
        prev_name = None
        linestring_points = []
        total_distance = 0

        for edge, next_edge, next_node_id in zip(edges, chain(edges[1:], [None]), node_ids[1:]):
            name = edge.name
            geom = edge.geom
            length = edge.meters

            reverse_geom = edge.start_node_id == next_node_id
            points = geom.coords[::-1] if reverse_geom else geom.coords

            start_bearing = self.get_bearing(*points[:2])
            end_bearing = self.get_bearing(*points[-2:])

            if next_edge is None:
                # Reached last edge
                linestring_points.extend(points)
            else:
                linestring_points.extend(points[:-1])

            total_distance += length

            if name and name == prev_name:
                stretch = stretches[-1]
                stretch['edges'].append(edge)
                stretch['length'] += length
                stretch['end_bearing'] = end_bearing
            else:
                # Start of a new stretch
                stretches.append({
                    'edges': [edge],
                    'length': length,
                    'toward_node_id': next_node_id if next_node_id > -1 else None,
                    'point': Point(*points[0]),
                    'start_bearing': start_bearing,
                    'end_bearing': end_bearing,
                })
                prev_name = name

        # Create directions from stretches.

        for prev_stretch, stretch in zip([None] + stretches[:-1], stretches):
            first_edge = stretch['edges'][0]
            length = stretch['length']
            start_bearing = stretch['start_bearing']
            toward_node_id = stretch['toward_node_id']

            if prev_stretch is None:
                # First edge in stretch
                turn = self.get_direction_from_bearing(start_bearing)
            else:
                # Remaining edges
                prev_end_bearing = prev_stretch['end_bearing']
                turn = self.calculate_way_to_turn(prev_end_bearing, start_bearing)

            direction = {
                'turn': turn,
                'name': first_edge.display_name,
                'type': first_edge.highway,
                'toward': toward_node_id,
                'distance': self.distance_dict(length),
                'point': stretch['point'],
                'edge_ids': [edge.id for edge in stretch['edges']]
            }

            directions.append(direction)

        # Get the toward street at the start of each stretch found in
        # the loop just above. This is deferred to here so that we can
        # fetch all the toward nodes up front with their associated
        # edges in a single query. This is much faster than processing
        # each node individually inside the loop--that causes up to 2*N
        # additional queries being issued to the database (fetching of
        # the inbound and outbound edges for the node).

        filter_ids = [direction['toward'] for direction in directions]
        if filter_ids:
            q = self.session.query(Intersection)
            q = q.filter(Intersection.id.in_(filter_ids))
            q = q.options(joinedload(Intersection.streets))
            node_map = {node.id: node for node in q}
        else:
            node_map = {}

        for direction in directions:
            name = direction['name']
            toward_node_id = direction['toward']
            if toward_node_id is None:
                # This is a special case where the destination is within
                # an edge (i.e., it's a street address) AND there are no
                # intersections between the last turn and the
                # (synthetic) destination node. In this case, since the
                # destination node doesn't have any intersecting edges,
                # a toward street can't be determined. Also, the
                # destination node won't have been fetched in the query
                # above because it doesn't really exist.
                toward = 'your destination'
            else:
                node = node_map[toward_node_id]
                toward = self.get_different_name_from_intersection(name, node)
            direction['toward'] = toward

        # TODO: Extract jogs?

        linestring = LineString(linestring_points)
        distance = self.distance_dict(total_distance)
        return directions, linestring, distance

    def distance_dict(self, meters):
        return {
            'meters': meters,
            'kilometers': meters * 0.001,
            'feet': meters * 3.28084,
            'miles': meters * 0.0006213712,
        }

    def get_different_name_from_intersection(self, name, node):
        """Get a street name from ``node`` that's not ``name``.

        If there is no such cross street, ``None`` is returned instead.

        """
        for street in node.streets:
            other_name = street.name
            if other_name and other_name != name:
                return other_name

    def get_bearing(self, p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        deg = degrees(atan2(dx, dy))
        while deg < 0:
            deg += 360
        return deg

    def calculate_way_to_turn(self, old_bearing, new_bearing):
        """Given two bearings in [0, 360], return the associated turn.

        Return a string such as "right" or "straight".

        """
        diff = new_bearing - old_bearing
        while diff < 0:
            diff += 360
        while diff > 360:
            diff -= 360
        if 0 <= diff < 10:
            way = 'straight'
        elif 10 <= diff <= 170:
            way = 'right'
        elif 170 < diff < 190:
            way = 'back'
        elif 190 <= diff <= 350:
            way = 'left'
        elif 350 < diff <= 360:
            way = 'straight'
        else:
            raise ValueError(
                'Could not calculate way to turn from {} and {}'
                .format(new_bearing, old_bearing))
        return way

    def get_direction_from_bearing(self, bearing):
        """Translate ``bearing`` to a cardinal direction."""
        buckets = {
            0: 'north',
            1: 'northeast',
            2: 'east',
            3: 'southeast',
            4: 'south',
            5: 'southwest',
            6: 'west',
            7: 'northwest',
        }
        bucket = int((bearing + 22.5) / 45) % 8
        return buckets[bucket]
