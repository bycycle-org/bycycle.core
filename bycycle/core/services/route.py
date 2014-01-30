"""Provides route finding via the `query` method of the `Service` class.

Currently routing can only be done between two points. Some things have been
changed for eventual support for routing between more than two points; there's
still more to do though.

Here's what the route service does:

- Checks for at least two waypoints.

- Checks that none of the waypoints are blank.

- Geocodes each waypoint in the region specified by the user. The region is
  specified either explicitly or by including the city/state or zip code.

- Creates a travel mode that provides a cost function to the single-source
  shortest-paths algorithm. The default travel mode is bicycle. Other modes
  are supported, but none have been implemented.

- Fetches the adjacency matrix for the region.

- Inserts extra nodes and segments into the adjacency matrix for each geocode
  that is within an edge (as opposed to being at a node).

- Attempts to find a route between the geocodes, in the order they were
  given by the user.

- Returns a `Route` object that includes turn-by-turn directions, distance,
  and other information about the route found.

"""
import dijkstar

from shapely.geometry import Point, LineString

from sqlalchemy.orm import joinedload

from bycycle.core.util import gis

from bycycle.core.model.geocode import IntersectionGeocode
from bycycle.core.model.route import Route

from bycycle.core import services
from bycycle.core.services import geocode
from bycycle.core.services.exceptions import (
    ByCycleError, InputError, NotFoundError)


class RouteError(ByCycleError):

    title = 'Route Service Error'
    description = ('An error was encountered in the routing service. '
                   'Further information is unavailable')

    def __init__(self, description=None):
        ByCycleError.__init__(self, description)


class EmptyGraphError(RouteError):

    title = 'Empty Routing Graph'
    description = ('The routing graph is empty, which really should not even'
                   'be possible.')

    def __init__(self):
        RouteError.__init__(self)


class NoRouteError(RouteError, NotFoundError):

    title = 'Route Not Found'

    def __init__(self, start_geocode, end_geocode, region):
        self.start_geocode = start_geocode
        self.end_geocode = end_geocode
        self.region = region
        desc = (
            'Unable to find a route from "%s" to "%s" in region "%s"' % (
                str(start_geocode.address).replace('\n', ', '),
                str(end_geocode.address).replace('\n', ', '),
                region
            )
        )
        RouteError.__init__(self, desc)


class MultipleMatchingAddressesError(RouteError):

    title = 'Multiple Matching Addresses Found'
    description = ('Multiple addresses were found that match one or more '
                   'input addresses.')

    def __init__(self, choices=None):
        self.choices = choices
        RouteError.__init__(self)


class Service(services.Service):
    """Route-finding Service."""
    name = 'route'

    def query(self, q, tmode='bicycle', pref='', **kwargs):
        """Get a route for all the addresses in ``q`` [0 ==> 1 ==> 2 ...].

        ``q`` list<string>
            A list of addresses to be normalized, geocoded, and routed
            between.

        return `Route`
            A `Route` between all the addresses in ``q``.

        raise `InputError`
            Less than 2 addresses given or an address is blank.

        raise `InputError`, `ValueError`
            Raised in the normaddr and geocode queries. Look there for details.

        raise `AddressNotFoundError`
            Any of the addresses in ``q`` can't be geocoded

        raise `MultipleMatchingAddressesError`
            Multiple addresses found for any of the addresses in ``q``

        raise `NoRouteError`
            No route found between start and end addresses

        """
        self.query_kwargs = kwargs

        # Process input waypoints (does basic error checking)
        waypoints = self._getWaypoints(q)

        # Get geocodes matching waypoints
        #   * Might raise ``MultipleMatchingAddressesError``
        #   * Might initialize ``self.region``
        geocodes = self._getGeocodes(waypoints)

        # Get weight function for specified travel mode
        path = 'bycycle.core.model.%s.%s' % (self.region.slug, tmode)
        module = __import__(path, globals(), locals(), [''])
        mode = module.TravelMode(self.region, pref=pref)
        getEdgeWeight = mode.getEdgeWeight
        getHeuristicWeight = mode.getHeuristicWeight

        # Fetch the adjacency matrix
        G = self.region.matrix
        if not G:
            raise EmptyGraphError()

        # Get paths between adjacent waypoints
        paths_info = []
        for s, e in zip(geocodes[:-1], geocodes[1:]):
            # path_info: node_ids, edge_attrs, split_edges
            path_info = self._getPathBetweenGeocodes(
                s, e, G, getEdgeWeight, getHeuristicWeight
            )
            paths_info.append(path_info)

        # Convert paths to `Route`s
        routes = []
        starts = geocodes[:-1]
        ends = geocodes[1:]
        # for start/end original, start/end geocode, path...
        for start, end, path_info in zip(starts, ends, paths_info):
            # route_data: nodes, edges, directions, linestring, distance
            route_data = self._makeDirectionsForPath(*path_info)
            route = Route(self.region, start, end, *route_data)
            routes.append(route)
        if len(routes) == 1:
            return routes[0]
        else:
            return routes

    def _getWaypoints(self, q):
        """Check the waypoints in ``q`` and return a new list of waypoints.

        ``q`` `sequence` -- A sequence of waypoint strings.

        return `list` of `str` -- A list of waypoints with leading & trailing
        whitespace removed.

        raise `InputError` -- There are less than 2 waypoints or any of the
        waypoints is blank (an empty string).

        """
        errors = []
        waypoints = [(w or '').strip() for w in q]
        num_waypoints = len(waypoints)
        if num_waypoints == 0:
            errors.append('Please enter start and end addresses.')
        if num_waypoints == 1:
            # Make sure there are at least two waypoints
            errors.append('Please enter an end address.')
        else:
            # Make sure waypoints are not blank
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
        # Let multiple input errors fall through to here
        if errors:
            raise InputError(errors)
        return waypoints

    def _getGeocodes(self, waypoints):
        """Return a `list` of `Geocode`s associated with each ``waypoint``."""
        geocode_service = geocode.Service(region=self.region)
        geocodes = []
        addresses_not_found = []
        multiple_match_found = False
        choices = []
        for w in waypoints:
            try:
                geocode_ = geocode_service.query(w, **self.query_kwargs)
            except geocode.AddressNotFoundError:
                addresses_not_found.append(w)
            except geocode.MultipleMatchingAddressesError as e:
                multiple_match_found = True
                choices.append(e.geocodes)
            else:
                geocodes.append(geocode_)
                choices.append(geocode_)
                if not self.region and geocode_service.region:
                    self.region = geocode_service.region
        if addresses_not_found:
            raise geocode.MultipleAddressesNotFoundError(addresses_not_found,
                                                         self.region)
        elif multiple_match_found:
            raise MultipleMatchingAddressesError(choices=choices)
        return geocodes

    def _getPathBetweenGeocodes(self,
                                start_geocode, end_geocode, G,
                                getEdgeWeight, getHeuristicWeight):
        """Try to find a path between the start and end geocodes.

        A path in this case is a set of ordered node and edge IDs.

        ``start_geocode`` `Geocode` -- An object that has a geographic
        coordinate and a network ID. The network ID is what we need here.

        ``end_geocode`` `Geocode` -- Same as ``start_geocode`` but for the
        end of the path.

        ``G`` `dict` -- The adjacency matrix to send to the path-finding
        algorithm.

        ``getEdgeWeight``

        ``getHeuristicWeight``

        return `tuple` -- Node IDs, Edge attributes, Split Edges

        """
        if start_geocode == end_geocode:
            raise InputError('Start and end addresses appear to be the same.')

        ### Get the start and end nodes for path finding. G may be updated.

        # A place to save the new edges formed from splitting an edge when a
        # geocode is within an edge. This saving happens as a side effect in
        # _getNodeForGeocode.
        split_edges = []
        H = dijkstar.Graph()

        # Get start node
        node_id, edge_f_id, edge_t_id = -1, -1, -2
        start_node = self._getNodeForGeocode(start_geocode, G, H,
                                             node_id, edge_f_id, edge_t_id,
                                             split_edges)
        # Get end node
        node_id, edge_f_id, edge_t_id = -2, -3, -4
        end_node = self._getNodeForGeocode(end_geocode, G, H,
                                           node_id, edge_f_id, edge_t_id,
                                           split_edges)

        ### All set up--try to find a path in G between the start and end nodes
        try:
            nodes, edge_attrs, costs, total_weight = dijkstar.find_path(
                G,
                start_node.id, end_node.id,
                H,
                cost_func=getEdgeWeight,
                heuristic_func=getHeuristicWeight
            )
        except dijkstar.NoPathError:
            raise NoRouteError(start_geocode, end_geocode, self.region)

        return nodes, edge_attrs, split_edges

    def _getNodeForGeocode(self,
                           geocode_,
                           G, H,
                           node_id, edge_f_id, edge_t_id,  # synthetic
                           split_edges):
        """Get or synthesize `Node` for ``geocode``.

        If the geocode is at an intersection, just return its `node`;
        otherwise, synthesize and return a mid-block `Node`.

        """
        if isinstance(geocode_, IntersectionGeocode):
            # Geocode is at a node--easy case
            node = geocode_.node
        else:
            # Geocode is on an edge--hard case
            edge = geocode_.edge
            node_f, node_t = edge.node_f, edge.node_t
            node_f_id, node_t_id = node_f.id, node_t.id

            # edge_f goes from node_f to split
            # edge_t goes from split to node_t
            edge_f, edge_t = edge.splitAtGeocode(
                geocode_, node_id, edge_f_id, edge_t_id
            )
            split_edges += [edge_f, edge_t]

            Node = self.region.module.Node
            node = Node(id=node_id, geom=geocode_.xy)
            node.edges_f.append(edge_f)
            node.edges_t.append(edge_t)

            # Graft node_f and node_t onto H
            H.add_node(node_f_id, G[node_f_id])
            H.add_node(node_t_id, G[node_t_id])

            edge_f_attrs = self.region.convert_edge_for_matrix(edge_f)
            edge_t_attrs = self.region.convert_edge_for_matrix(edge_t)

            # If node_f connects to node_t
            if node_t_id in G[node_f_id]:
                # Add edge from node_f to split node and from split node
                # to node_t
                H.add_edge(node_f_id, node_id, edge_f_attrs)
                H.add_edge(node_id, node_t_id, edge_t_attrs)
                # Disallow traversal directly from node_f to node_t
                del H[node_f_id][node_t_id]

            # If node_t connects to node_f
            if node_f_id in G[node_t_id]:
                # Add edge from node_t to split node and from split node
                # to node_f
                H.add_edge(node_t_id, node_id, edge_t_attrs)
                H.add_edge(node_id, node_f_id, edge_f_attrs)
                # Disallow traversal directly from node_t to node_f
                del H[node_t_id][node_f_id]

        return node

    def _makeDirectionsForPath(self, node_ids, edge_attrs, split_edges):
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
                     'blocks': 1
                 },
                 'bikemodes': ['l', ...],
                 'jogs': [{'turn': 'left', 'street': 'ne 7th ave'}, ...]
               }

            * A linestring, which is a list of x, y coords. Each coordinate
              has the following form:
              {
                'x': -122,
                'y': -45
              }

            * A `dict` of total distances in units of feet, miles, kilometers,
              and blocks:
              {
                'feet': 5487,
                'miles': 1.04,
                'kilometers': 1.11,
                'blocks': 9
              }

        """
        Edge = self.region.module.Edge
        Node = self.region.module.Node

        directions = []
        linestring = None
        distance = {}
        edge_ids = [attrs[0] for attrs in edge_attrs]

        # Get edges along path
        q = Edge.q().filter(Edge.id.in_(edge_ids))
        q = q.options(joinedload(Edge.node_f))
        q = q.options(joinedload(Edge.node_t))
        q = q.options(joinedload(Edge.street_name))
        # Make sure they're in path order
        edge_map = {e.id: e for e in q}
        edge_map.update({e.id: e for e in split_edges})
        edges = [edge_map[i] for i in edge_ids]

        # Get the actual edge lengths since modified weights might have been
        # used to find the path
        edge_lengths = [e.to_feet() for e in edges]
        total_length = sum(edge_lengths)
        blocks = int(round(total_length / self.region.block_length))
        distance.update({
            'feet': total_length,
            'miles': total_length / 5280.0,
            'kilometers': total_length / 5280.0 * 1.609344,
            'blocks': blocks,
        })

        # Get bearing of first and last segment of each edge. We use this
        # later to calculate turns from one edge to another--turning from
        # heading in an `end_bearing` direction to a `bearing` direction. This
        # also gathers up all the points for the overall linestring (for the
        # whole route).
        bearings = []
        end_bearings = []
        linestring_points = []
        for node_t_id, e in zip(node_ids[1:], edges):
            geom = e.geom  # Current edge's linestring
            points = list(geom.coords)
            if e.node_f_id == node_t_id:
                # Moving to => from on arc; reverse geometry
                points.reverse()

            # Append all but last point in current edge's linestring. This
            # avoids duplicate points at intersections--below we'll have to
            # append the last point for the last edge.
            linestring_points += points[:-1]

            # *b------e* b is bearing of first segment in edge; e is bearing
            # of last segment in edge
            _f = gis.getBearingGivenStartAndEndPoints
            bearings.append(_f(Point(points[0]), Point(points[1])))
            end_bearings.append(_f(Point(points[-2]), Point(points[-1])))

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
            street_name = e.street_name
            street_names.append(street_name)  # save for later
            try:
                next_e = edges[i + 1]
            except IndexError:
                next_street_name = None
            else:
                next_street_name = next_e.street_name
            if street_name and street_name.almostEqual(prev_street_name):
                edge_lengths[stretch_start_i] += edge_lengths[i]
                edge_lengths[i] = None
                prev_street_name = street_name
            # Check for jog
            elif (prev_street_name and
                  edge_lengths[i] < self.region.jog_length and
                  street_name != prev_street_name and
                  prev_street_name.almostEqual(next_street_name)):
                edge_lengths[stretch_start_i] += edge_lengths[i]
                edge_lengths[i] = None
                turn = self._calculateWayToTurn(
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
        for node_t_id, e, length in zip(node_ids[1:], edges, edge_lengths):
            node_t = e.node_t if node_t_id == e.node_t.id else e.node_f

            street_name = street_names[edge_count]
            str_street_name = str(street_name)

            if length is not None:  # Only do this at the start of a stretch
                bearing = bearings[edge_count]
                # TODO: Create a Direction class???
                direction = {
                    'turn': '', 'street': '', 'toward': '', 'bikemodes': [],
                    'linestring_index': linestring_index,
                    'jogs': jogs[directions_count],
                    'distance': {
                        'feet': length, 'miles': length / 5280.0,
                        'kilometers': length / 5280.0 * 1.609344,
                        'blocks': length / self.region.block_length
                    }
                }

                []
                # Get direction of turn and street to turn onto
                if first:
                    first = False
                    turn = self._getDirectionFromBearing(bearing)
                    street = str_street_name
                else:
                    turn = self._calculateWayToTurn(
                        stretch_end_bearing, bearing)
                    if turn == 'straight':
                        # Go straight onto next street
                        # ('street a becomes street b')
                        street = [stretch_end_name, str_street_name]
                    else:
                        # Turn onto next street
                        street = str_street_name

                # This will be used below to get a street name from one
                # of the cross streets at the intersection we're headed
                # toward at the start of this stretch.
                toward_args.append((street_name, node_t_id))

                direction.update(dict(turn=turn, street=street))
                directions.append(direction)
                directions_count += 1

            # Save bearing if this edge is the last edge in a stretch
            try:
                if node_t and edge_lengths[edge_count + 1]:
                    stretch_end_bearing = end_bearings[edge_count]
                    stretch_end_name = str_street_name
            except IndexError:
                pass

            # Add edge's bikemode to list of bikemodes for current
            # stretch if it's different from the bikemode of the
            # previous edge.
            if e.bikemode:
                bikemodes = direction['bikemodes']
                if not bikemodes or bikemodes[-1] != e.bikemode:
                    bikemodes.append(e.bikemode)

            edge_count += 1
            linestring_index += len(e.geom.coords) - 1

        # Get the toward street at the start of each stretch found in
        # the loop just above. This is deferred to here so that we can
        # fetch all the toward nodes up front with their associated
        # edges in a single query.  This is much faster than processing
        # each node individually inside the loop--that causes up to 2*N
        # additional queries being issued to the database (fetching of
        # the inbound and outbound edges for the node).
        q = Node.q()
        q = q.filter(Node.id.in_(i[1] for i in toward_args))
        q = q.options(joinedload(Node.edges_f))
        q = q.options(joinedload(Node.edges_t))
        node_map = {n.id: n for n in q}
        for d, (st_name, node_id) in zip(directions, toward_args):
            if node_id < 0:
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
                node = node_map[node_id]
                toward = self._getDifferentStreetNameFromNode(st_name, node)
            d['toward'] = toward

        return directions, linestring, distance

    def _getNameAndType(self, street_name):
        try:
            name, sttype = street_name.name, street_name.sttype
        except AttributeError:
            return None
        return name, sttype

    def _getDifferentStreetNameFromNode(self, street_name, node):
        """Get different street name from ``node``."""
        name_type = self._getNameAndType(street_name)
        for edge in node.edges:
            sn = edge.street_name
            other_name_type = self._getNameAndType(sn)
            if other_name_type != name_type:
                return str(sn or '[No Name]')
        return ''

    def _calculateWayToTurn(self, old_bearing, new_bearing):
        """Given two bearings in [0, 360] gives the turn to go from old to new.

        ``new_bearing`` -- The bearing of the new direction of travel.
        ``old_bearing`` -- The bearing of the old direction of travel.

        return `string` -- The way to turn to get from going in the old
        direction to get going in the new direction ('right', 'left',
        etc.).

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
                'Could not calculate way to turn from %s and %s' %
                (new_bearing, old_bearing)
            )
        return way

    def _getDirectionFromBearing(self, bearing):
        """Translate ``bearing`` to a cardinal direction."""
        arc = 45
        half_arc = arc * .5
        n = (360 - half_arc, half_arc)
        ne = (n[1], n[1] + arc)
        e = (ne[1], ne[1] + arc)
        se = (e[1], e[1] + arc)
        s = (se[1], se[1] + arc)
        sw = (s[1], s[1] + arc)
        w = (sw[1], sw[1] + arc)
        nw = (w[1], w[1] + arc)
        if 0 <= bearing < n[1]:
            return 'north'
        elif n[0] < bearing <= 360:
            return 'north'
        elif ne[0] < bearing <= ne[1]:
            return 'northeast'
        elif e[0] < bearing <= e[1]:
            return 'east'
        elif se[0] < bearing <= se[1]:
            return 'southeast'
        elif s[0] < bearing <= s[1]:
            return 'south'
        elif sw[0] < bearing <= sw[1]:
            return 'southwest'
        elif w[0] < bearing <= w[1]:
            return 'west'
        elif nw[0] < bearing <= nw[1]:
            return 'northwest'
