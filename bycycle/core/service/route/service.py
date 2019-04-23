import io
import threading
from math import atan2, degrees

import dijkstar

from sqlalchemy.orm import joinedload

from tangled.util import load_object

from bycycle.core.exc import InputError
from bycycle.core.geometry import split_line, LineString
from bycycle.core.model import Graph, Intersection, Route, Street
from bycycle.core.service import AService, LookupService
from bycycle.core.service.lookup import MultipleLookupResultsError

from .exc import EmptyGraphError, MultipleRouteLookupResultsError, NoRouteError


GRAPH = None
GRAPH_LOCK = threading.Lock()


# XXX: Loading the entire graph into memory isn't scalable.
#      Also the current approach doesn't allow for selecting
#      a different graph depending on the mode (or any other
#      criteria).
def get_graph(session):
    global GRAPH
    if GRAPH is None:
        with GRAPH_LOCK:
            if GRAPH is None:
                q = session.query(Graph).order_by(Graph.timestamp.desc())
                graph = q.first()
                file = io.BytesIO()
                file.write(graph.data)
                file.seek(0)
                GRAPH = dijkstar.Graph.unmarshal(file)
                if not GRAPH:
                    raise EmptyGraphError()
    return GRAPH


class RouteService(AService):

    """Route-finding Service."""

    name = 'route'

    def query(self, q, cost_func='bicycle', heuristic_func=None, points=None):
        waypoints = self.get_waypoints(q, points)
        graph = get_graph(self.session)

        if ':' in cost_func:
            cost_func = load_object(cost_func)
        else:
            cost_func = load_object('.cost', cost_func)

        paths_info = []
        for s, e in zip(waypoints[:-1], waypoints[1:]):
            path_info = self.find_path(
                graph, s, e, cost_func=cost_func, heuristic_func=heuristic_func)
            paths_info.append(path_info)

        routes = []
        starts = waypoints[:-1]
        ends = waypoints[1:]

        for start, end, path_info in zip(starts, ends, paths_info):
            node_ids, edge_attrs, split_ways = path_info
            directions, linestring, distance = self.make_directions(node_ids, edge_attrs, split_ways)
            route = Route(start, end, directions, linestring, distance)
            routes.append(route)

        return routes[0] if len(routes) == 1 else routes

    def get_waypoints(self, q, points=None):
        errors = []
        waypoints = [w.strip() for w in q]
        num_waypoints = len(waypoints)
        points = points or [None] * num_waypoints
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
        lookup_service = LookupService(self.session)
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

    def find_path(self, graph, s, e, cost_func=None, heuristic_func=None):
        start = s.closest_object
        end = e.closest_object
        annex = None
        split_ways = {}

        if isinstance(start, Street) or isinstance(end, Street):
            annex = dijkstar.Graph()

        if isinstance(start, Street):
            start, *start_ways = self.split_way(start, s.geom, -1, -1, -2, graph, annex)
            split_ways.update({w.id: w for w in start_ways})

        if isinstance(end, Street):
            end, *end_ways = self.split_way(end, e.geom, -2, -3, -4, graph, annex)
            split_ways.update({w.id: w for w in end_ways})

        try:
            nodes, edge_attrs, costs, total_weight = dijkstar.find_path(
                graph, start.id, end.id,
                annex=annex, cost_func=cost_func, heuristic_func=heuristic_func)
        except dijkstar.NoPathError:
            raise NoRouteError(s, e)

        assert nodes[0] == start.id
        assert nodes[-1] == end.id

        return nodes, edge_attrs, split_ways

    def split_way(self, way, point, node_id, way1_id, way2_id, graph, annex):
        start_node_id, end_node_id = way.start_node.id, way.end_node.id

        line1, line2 = split_line(way.geom, point)
        shared_node = Intersection(id=node_id, geom=point)
        way1 = way.clone(id=way1_id, end_node_id=node_id, end_node=shared_node, geom=line1)
        way2 = way.clone(id=way2_id, start_node_id=node_id, start_node=shared_node, geom=line2)

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
            address like "123 Main St")

        return
            * A list of directions. Each direction has the following form::

              {
                  'turn': 'left',
                  'name': 'SE Stark St',
                  'display_name': 'SE Stark St',
                  'type': 'residential',
                  'toward': 'SE 45th Ave',
                  'distance': {
                       'feet': 264.0,
                       'miles': 0.05,
                       'meters': 80.0,
                       'kilometers': 0.08,
                   },
                   'jogs': [{'turn': 'left', 'name': 'NE 7th Ave'}, ...]
               }

            * A linestring, which is a list of x, y coords:

              [(x, y), ...]

            * A `dict` of total distances in units of feet, miles, kilometers:

              {
                  'feet': 5487.0,
                  'miles': 1.04,
                  'meters': 1110.0,
                  'kilometers': 1.11,
              }

        """
        directions = []

        # Gather edges into a list.

        edges = []
        edge_ids = [attrs[0] for attrs in edge_attrs]

        if edge_ids and edge_ids[0] < 0:
            edges.append(split_edges[edge_ids[0]])

        filter_ids = [i for i in edge_ids if i > 0]
        if filter_ids:
            q = self.session.query(Street).filter(Street.id.in_(filter_ids))
            q = q.options(joinedload(Street.start_node))
            q = q.options(joinedload(Street.end_node))
            edge_map = {edge.id: edge for edge in q}
            edges.extend(edge_map[i] for i in filter_ids)

        if len(edge_ids) > 1 and edge_ids[-1] < 0:
            edges.append(split_edges[edge_ids[-1]])

        # Group edges together by street name into stretches.

        start_edges = []
        prev_name = None
        prev_end_bearing = None
        linestring_points = []
        loop_data = zip(node_ids[1:], edges, [None] + edges[:-1], edges[1:] + [None])

        for node_id, edge, prev_edge, next_edge in loop_data:
            length = edge.meters
            name = edge.name or edge.highway

            points = edge.geom.coords
            if edge.start_node.id == node_id:
                points = points[::-1]

            start_bearing = self.get_bearing(*points[:2])
            end_bearing = self.get_bearing(*points[-2:])

            if next_edge is None:
                # Reached last edge
                next_name = None
                linestring_points.extend(points)
            else:
                next_name = next_edge.name or next_edge.highway
                linestring_points.extend(points[:-1])

            if name and name == prev_name:
                start_edge = start_edges[-1]
                start_edge['edges'].append(edge)
                start_edge['end_bearing'] = end_bearing
            elif (prev_name and
                  length < 30 and  # 30 meters TODO: Magic number
                  name != prev_name and
                  prev_name == next_name):
                start_edge = start_edges[-1]
                start_edge['jogs'].append({
                    'edge': edge,
                    'start_point': points[0],
                    'start_bearing': start_bearing,
                    'end_bearing': end_bearing,
                    'prev_end_bearing': prev_end_bearing,
                })
            else:
                # Start of a new stretch
                start_edges.append({
                    'edge': edge,
                    'edges': [edge],
                    'jogs': [],
                    'toward_node_id': node_id,
                    'start_point': points[0],
                    'start_bearing': start_bearing,
                    'end_bearing': end_bearing,
                })
                prev_name = name

            prev_end_bearing = end_bearing

        # Create directions from stretches.

        for prev_start_edge, start_edge in zip([None] + start_edges[:-1], start_edges):
            edge = start_edge['edge']
            length = sum(edge.meters for edge in start_edge['edges'])
            jogs = start_edge['jogs']
            start_bearing = start_edge['start_bearing']
            toward_node_id = start_edge['toward_node_id']

            if prev_start_edge is None:
                # First
                turn = self.get_direction_from_bearing(start_bearing)
            else:
                prev_end_bearing = prev_start_edge['end_bearing']
                turn = self.calculate_way_to_turn(prev_end_bearing, start_bearing)

            processed_jogs = []
            for jog in jogs:
                jog_edge = jog['edge']
                processed_jogs.append({
                    'turn': self.calculate_way_to_turn(
                        jog['prev_end_bearing'], jog['start_bearing']),
                    'name': jog_edge.name or jog_edge.highway,
                    'display_name': jog_edge.display_name,
                })

            direction = {
                'turn': turn,
                'name': name,
                'display_name': edge.display_name,
                'type': edge.highway,
                'toward': toward_node_id,
                'jogs': processed_jogs,
                'distance': self.distance_dict(length),
                'start_point': start_edge['start_point'],
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
            if toward_node_id < 0:
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
                node = node_map[toward_node_id]
                toward = self.get_different_name_from_intersection(name, node)
            direction['toward'] = toward

        linestring = LineString(linestring_points)
        distance = self.distance_dict(sum(edge.meters for edge in edges))
        return directions, linestring, distance

    def distance_dict(self, meters):
        return {
            'meters': meters,
            'kilometers': meters * 0.001,
            'feet': meters * 3.28084,
            'miles': meters * 0.000621371,
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
