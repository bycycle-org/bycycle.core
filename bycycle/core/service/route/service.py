from collections import namedtuple
from math import atan2, degrees

import dijkstar

from sqlalchemy.orm import joinedload

from tangled.util import asset_path, load_object

from bycycle.core.model.route import Route

from bycycle.core.exc import InputError
from bycycle.core.geometry import LineString, Point
from bycycle.core.model import Intersection, Street
from bycycle.core.service import AService, LookupService

from .exc import EmptyGraphError, MultipleLookupResultsError, NoRouteError


graph = None


Toward = namedtuple('Toward', ('street_name', 'node_id'))


class RouteService(AService):

    """Route-finding Service."""

    name = 'route'

    def query(self, q, cost_func='bicycle', ids=None, points=None):
        waypoints = self.get_waypoints(q, ids, points)

        # XXX: Loading the entire graph into memory isn't scalable.
        #      Also the current approach doesn't allow for selecting
        #      a different graph depending on the mode (or any other
        #      criteria).
        global graph
        if graph is None:
            graph = dijkstar.Graph.unmarshal(asset_path('bycycle.core:matrix'))
        if not graph:
            raise EmptyGraphError()

        if ':' in cost_func:
            cost_func = load_object(cost_func)
        else:
            cost_func = load_object('.cost', cost_func)

        paths_info = []
        for s, e in zip(waypoints[:-1], waypoints[1:]):
            # path_info: node_ids, edge_attrs, split_edges
            path_info = self.find_path(graph, s, e, cost_func=cost_func)
            paths_info.append(path_info)

        # Convert paths to `Route`e
        routes = []
        starts = waypoints[:-1]
        ends = waypoints[1:]
        # for start/end original, start/end geocode, path...
        for start, end, path_info in zip(starts, ends, paths_info):
            # route_data: nodes, edges, directions, linestring, distance
            route_data = self.make_directions(*path_info)
            route = Route(start, end, *route_data)
            routes.append(route)
        if len(routes) == 1:
            return routes[0]
        else:
            return routes

    def get_waypoints(self, q, ids=None, points=None):
        errors = []
        waypoints = [w.strip() for w in q]
        num_waypoints = len(waypoints)
        if ids is None:
            ids = [None] * num_waypoints
        if points is None:
            points = [None] * num_waypoints
        if num_waypoints == 0:
            errors.append('Please enter start and end addresses.')
        if num_waypoints == 1:
            errors.append('Please enter an end address.')
        else:
            if num_waypoints == 2:
                if not waypoints[0]:
                    errors.append('Please enter a start address.')
                if not waypoints[-1]:
                    errors.append('Please enter an end address.')
            else:
                for w in waypoints:
                    if not w:
                        errors.append('Addresses cannot be blank.')
                        break
        if errors:
            raise InputError(errors)
        lookup_service = LookupService(self.session)
        results = []
        raise_multi = False
        for w, id_hint, point_hint in zip(waypoints, ids, points):
            result = lookup_service.query(w, id_hint, point_hint)
            if isinstance(result, (list, tuple)):
                raise_multi = True
            results.append(result)
        if raise_multi:
            raise MultipleLookupResultsError(choices=results)
        return results

    def find_path(self, graph, s, e, cost_func=None, heuristic_func=None):
        start = s.closest_object
        end = e.closest_object
        annex = None
        split_ways = []

        if isinstance(start, Street) or isinstance(end, Street):
            annex = dijkstar.Graph()

        if isinstance(start, Street):
            start_node, *start_ways = self.split_way(
                start, s.geom, -1, -1, -2, graph, annex)
            split_ways += start_ways
        else:
            start_node = start

        if isinstance(end, Street):
            end_node, *end_ways = self.split_way(
                end, e.geom, -2, -3, -4, graph, annex)
            split_ways += end_ways
        else:
            end_node = end

        try:
            nodes, edge_attrs, costs, total_weight = dijkstar.find_path(
                graph, start_node.id, end_node.id, annex, cost_func=cost_func,
                heuristic_func=heuristic_func)
        except dijkstar.NoPathError:
            raise NoRouteError(s, e)

        return nodes, edge_attrs, split_ways

    def split_way(self, way, point, node_id, way1_id, way2_id, graph, annex):
        start_node_id, end_node_id = way.start_node.id, way.end_node.id
        shared_node, way1, way2 = way.split(point, node_id, way1_id, way2_id)

        # Graft start node and end node of way onto annex
        annex[start_node_id] = graph[start_node_id].copy()
        annex[end_node_id] = graph[end_node_id].copy()

        way1_attrs = (
            way1.id, way1.meters, way1.name, way1.highway, way1.bicycle,
            way1.foot, way1.sidewalk)
        way2_attrs = (
            way2.id, way2.meters, way2.name, way2.highway, way2.bicycle,
            way2.foot, way2.sidewalk)

        # If start node => end node, add a edge from start node to split
        # node and from split node to end node.
        if end_node_id in annex[start_node_id]:
            annex.add_edge(start_node_id, node_id, way1_attrs)
            annex.add_edge(node_id, end_node_id, way2_attrs)
            # Disallow traversal directly from start node to end node
            del annex[start_node_id][end_node_id]

        # If end node => start node, add edge from end node to split
        # node and from split node to start node.
        if start_node_id in annex[end_node_id]:
            annex.add_edge(end_node_id, node_id, way2_attrs)
            annex.add_edge(node_id, start_node_id, way1_attrs)
            # Disallow traversal directly from end node to start node
            del annex[end_node_id][start_node_id]

        return shared_node, way1, way2

    def make_directions(self, node_ids, edge_attrs, split_edges):
        """Process the shortest path into a nice list of directions.

        ``node_ids``
            The IDs of the nodes on the route

        ``edges_attrs``
            The attributes of the edges on the route as a list or tuple.
            The first item in each list must be the edge ID.

        ``split_edges``
            Temporary edges formed by splitting an existing edge when the
            start and/or end of a route is within an edge (e.g., for an
            address like "123 Main St"

        return
            * A list of directions. Each direction has the following form:
              {
                'turn': 'left',
                'street': 'se stark st'
                'toward': 'se 45th ave'
                'linestring_index': 3,  # index of start point in overall LS
                'distance': {
                     'feet': 264,
                     'miles': .05,
                     'kilometers': .08,
                 },
                 'jogs': [{'turn': 'left', 'street': 'ne 7th ave'}, ...]
               }

            * A linestring, which is a list of x, y coords. Each coordinate
              has the following form:
              {
                'x': -122,
                'y': -45
              }

            * A `dict` of total distances in units of feet, miles, kilometers:
              {
                'feet': 5487,
                'miles': 1.04,
                'kilometers': 1.11,
              }

        """
        directions = []

        # Get edges along path
        edge_ids = [attrs[0] for attrs in edge_attrs]
        q = self.session.query(Street).filter(Street.id.in_(edge_ids))
        q = q.options(joinedload(Street.start_node))
        q = q.options(joinedload(Street.end_node))

        # Make sure they're in path order
        edge_map = {e.id: e for e in q}
        edge_map.update({e.id: e for e in split_edges})
        edges = [edge_map[i] for i in edge_ids]

        edge_lengths = [e.meters for e in edges]
        distance = self.distance_dict(sum(edge_lengths))

        # Get bearing of first and last segment of each edge. We use this
        # later to calculate turns from one edge to another--turning from
        # heading in an `end_bearing` direction to a `bearing` direction. This
        # also gathers up all the points for the overall linestring (for the
        # whole route).
        bearings = []
        end_bearings = []
        linestring_points = []
        for end_node_id, e in zip(node_ids[1:], edges):
            points = list(e.geom.coords)
            if e.start_node_id == end_node_id:
                # Moving to => from on arc; reverse geometry
                points.reverse()

            # Append all but last point in current edge's linestring. This
            # avoids duplicate points at intersections--below we'll have to
            # append the last point for the last edge.
            linestring_points += points[:-1]

            # *b------e* b is bearing of first segment in edge; e is bearing
            # of last segment in edge
            bearings.append(
                self.get_bearing(Point(points[0]), Point(points[1])))
            end_bearings.append(
                self.get_bearing(Point(points[-2]), Point(points[-1])))

        # Append very last point in the route, then create overall linestring
        linestring_points.append(points[-1])
        linestring = LineString(linestring_points)

        # Add the lengths of successive same-named edges and set the first of
        # the edges' length to that "stretch" length, while setting the
        # successive edges' lengths to `None`. In the next for loop below,
        # edges with length `None` are skipped.
        prev_street_name = None
        stretch_start_i = 0
        street_names = []
        jogs = []
        for i, e in enumerate(edges):
            street_name = e.name
            street_names.append(street_name)  # save for later
            try:
                next_e = edges[i + 1]
            except IndexError:
                next_street_name = None
            else:
                next_street_name = next_e.name
            if street_name and street_name == prev_street_name:
                edge_lengths[stretch_start_i] += edge_lengths[i]
                edge_lengths[i] = None
                prev_street_name = street_name
            # Check for jog
            elif (prev_street_name and
                  edge_lengths[i] < 30 and  # 30 meters TODO: Magic number
                  street_name != prev_street_name and
                  prev_street_name == next_street_name):
                edge_lengths[stretch_start_i] += edge_lengths[i]
                edge_lengths[i] = None
                turn = self.calculate_way_to_turn(
                    end_bearings[i - 1], bearings[i])
                jogs[-1].append({'turn': turn, 'street': str(street_name)})
            else:
                # Start of a new stretch (i.e., a new direction)
                stretch_start_i = i
                prev_street_name = street_name
                jogs.append([])

        # Make directions list, where each direction is for a stretch of the
        # route and a stretch consists of one or more edges that all have the
        # same name and type.
        edge_count = 0
        directions_count = 0
        linestring_index = 0
        toward_args = []
        first = True
        for end_node_id, e, length in zip(node_ids[1:], edges, edge_lengths):
            end_node = (
                e.end_node_id
                if end_node_id == e.end_node_id
                else e.start_node_id)

            street_name = street_names[edge_count]
            if street_name is None:
                street_name = '[{}]'.format(e.highway.replace('_', ' '))

            if length is not None:  # Only do this at the start of a stretch
                bearing = bearings[edge_count]
                direction = {
                    'turn': '',
                    'street': '',
                    'toward': '',
                    'linestring_index': linestring_index,
                    'jogs': jogs[directions_count],
                    'distance': self.distance_dict(length)
                }

                # Get direction of turn and street to turn onto
                if first:
                    first = False
                    turn = self.get_direction_from_bearing(bearing)
                    street = street_name
                else:
                    turn = self.calculate_way_to_turn(
                        stretch_end_bearing, bearing)
                    if turn == 'straight':
                        # Go straight onto next street
                        # ('street a becomes street b')
                        street = [stretch_end_name, street_name]
                    else:
                        # Turn onto next street
                        street = street_name

                # This will be used below to get a street name from one
                # of the cross streets at the intersection we're headed
                # toward at the start of this stretch.
                toward_args.append(Toward(street_name, end_node_id))

                direction.update(dict(turn=turn, street=street))
                directions.append(direction)
                directions_count += 1

            # Save bearing if this edge is the last edge in a stretch
            try:
                if end_node and edge_lengths[edge_count + 1]:
                    stretch_end_bearing = end_bearings[edge_count]
                    stretch_end_name = street_name
            except IndexError:
                pass

            edge_count += 1
            linestring_index += len(e.geom.coords) - 1

        # Get the toward street at the start of each stretch found in
        # the loop just above. This is deferred to here so that we can
        # fetch all the toward nodes up front with their associated
        # edges in a single query. This is much faster than processing
        # each node individually inside the loop--that causes up to 2*N
        # additional queries being issued to the database (fetching of
        # the inbound and outbound edges for the node).
        q = self.session.query(Intersection)
        q = q.filter(Intersection.id.in_(a.node_id for a in toward_args))
        q = q.options(joinedload(Intersection.streets))
        node_map = {n.id: n for n in q}
        for d, t in zip(directions, toward_args):
            if t.node_id < 0:
                # This is a special case where the destination is within
                # an edge (i.e., it's a street address) AND there are no
                # intersections between the last turn and the
                # (synthetic) destination node. In this case, since the
                # destination node doesn't have any intersecting edges,
                # a toward street can't be determined. Also, the
                # destination node won't have been fetched in the query
                # above because it doesn't really exist.
                toward = None
            else:
                node = node_map[t.node_id]
                toward = self.get_different_street_name_from_intersection(
                    t.street_name, node)
            d['toward'] = toward

        return directions, linestring, distance

    def distance_dict(self, meters):
        return {
            'meters': meters,
            'kilometers': meters * 0.001,
            'feet': meters * 3.28084,
            'miles': meters * 0.000621371,
        }

    def get_different_street_name_from_intersection(self, street_name, node):
        """Get a street name from ``node`` that's not ``street_name``.

        If there is no such cross street, ``None`` is returned instead.

        """
        for street in node.streets:
            other_name = street.name
            if other_name and other_name != street_name:
                return other_name

    def get_bearing(self, p1, p2):
        dx = p2.x - p1.x
        dy = p2.y - p1.y
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
