from itertools import chain
from pathlib import Path

import ijson

from shapely.geometry import LineString, Point, Polygon

from sqlalchemy.schema import Column
from sqlalchemy.sql import select
from sqlalchemy.types import BigInteger, Boolean
from sqlalchemy.dialects.postgresql import insert as pg_insert

from tangled.decorators import cached_property

from bycycle.core.geometry import DEFAULT_SRID
from bycycle.core.geometry.sqltypes import POINT
from bycycle.core.model import (
    get_engine,
    get_session_factory,
    Base,
    Intersection,
    Street,
    USPSStreetSuffix,
)
from bycycle.core.model.compass import directions_ftoa
from bycycle.core.model.street import base_cost
from bycycle.core.util import PeriodicRunner, Timer

from .graph import OSMGraphBuilder


class Node(Base):

    __tablename__ = 'osm_node'

    id = Column(BigInteger, primary_key=True)
    is_intersection = Column(Boolean, default=False)
    geom = Column(POINT(DEFAULT_SRID))


INTERSECTION_TABLE = Intersection.__table__
NODE_TABLE = Node.__table__
STREET_TABLE = Street.__table__
SUFFIX_TABLE = USPSStreetSuffix.__table__


def action(description=None):
    def wrapper(meth):
        meth.__action__ = Action(meth, action.order, description)
        return meth
    action.order += 1
    return wrapper


action.order = 0


class Action:

    def __init__(self, meth, order, description=None):
        self.meth = meth
        self.order = order
        if description is not None:
            self.description = description
        elif meth.__doc__:
            self.description = meth.__doc__.strip().split('\n')[0]
        else:
            self.description = meth.__name__.replace('_', ' ').capitalize()

    def __str__(self):
        return f'{self.order}: {self.description}'


class OSMImporter:

    """Imports ways and their start and end nodes.

    It's assumed that all of the ways in the input OSM file have a
    non-empty highway tag.

    Ways are split where they share a node with another way.

    Nodes used only for geometry are not inserted--only nodes that are
    at the start and end of a way are.

    Args:
        bbox (tuple): Bounding box
        data_directory: Directory containing OSM data files
        graph_path: Path to save graph to
        connection_args: A dictionary containing SQLAlchemy connection
            arguments
        actions: A list of actions to perform. By default all actions
            will be performed

    """

    def __init__(self, bbox, data_directory, graph_path, connection_args, streets=True,
                 places=True, actions=None):
        engine = get_engine(**connection_args)
        session_factory = get_session_factory(engine)
        self.bbox = bbox
        self.bounds = Polygon.from_bounds(*bbox)
        self.data_directory = Path(data_directory).resolve()
        self.graph_path = graph_path
        self.engine = engine
        self.session = session_factory()

        if actions:
            self.actions = [self.all_actions[i - 1] for i in actions]
        else:
            self.actions = []
            if streets:
                self.actions.extend(self.all_actions[:7])
            if places:
                self.actions.extend(self.all_actions[7:])

    def iter_nodes(self, file_name):
        path = self.data_directory / file_name
        with path.open() as fp:
            items = ijson.items(fp, 'elements.item')
            for item in items:
                if item['type'] == 'node':
                    yield item

    def iter_ways(self, file_name):
        path = self.data_directory / file_name
        with path.open() as fp:
            items = ijson.items(fp, 'elements.item')
            for item in items:
                if item['type'] == 'way':
                    yield item

    @cached_property
    def all_actions(self):
        actions = [
            attr.__action__
            for attr in self.__class__.__dict__.values()
            if hasattr(attr, '__action__')
        ]
        actions.sort(key=lambda act: act.order)
        return actions

    @cached_property
    def street_type_map(self):
        street_type_map = {}
        for r in self.session.execute(SUFFIX_TABLE.select()):
            street_type_map[r.name] = r.abbreviation
            street_type_map[r.alias] = r.abbreviation
        return street_type_map

    def run(self):
        session = self.session
        result = None
        action_timer = Timer()
        total_timer = Timer()
        total_timer.start()

        def status(for_action, timer, end=''):
            message = '\r{action.order}. {action.description}... {timer}'
            message = message.format(action=for_action, timer=timer)
            print(' ' * (len(message) + 20), message, sep='', end=end)

        try:
            for current_action in self.actions:
                with action_timer:
                    status(current_action, action_timer)
                    runner = PeriodicRunner(
                        target=status, args=(current_action, action_timer), interval=0.2)
                    runner.start()
                    if result is not None:
                        result = current_action.meth(self, result)
                    else:
                        result = current_action.meth(self)
                    runner.stop()
                    runner.join()
                    status(current_action, action_timer, end='\n')
        except KeyboardInterrupt:
            runner.stop()
            runner.join()
            session.rollback()
            print('\nAborted')
        except Exception as exc:
            runner.stop()
            runner.join()
            session.rollback()
            raise exc
        else:
            session.commit()
            total_timer.stop()
            print('Total time: {}'.format(total_timer))
        finally:
            session.close()

        print('Vacuuming tables...', end=' ', flush=True)
        self.vacuum(INTERSECTION_TABLE, STREET_TABLE)
        print('Done')

    @action()
    def drop_street_tables(self):
        tables = (NODE_TABLE, INTERSECTION_TABLE, STREET_TABLE)
        Base.metadata.drop_all(self.session.connection(), tables=tables)

    @action()
    def create_street_tables(self):
        tables = (NODE_TABLE, INTERSECTION_TABLE, STREET_TABLE)
        Base.metadata.create_all(self.session.connection(), tables=tables)

    @action()
    def find_intersections(self):
        """Find intersection nodes"""
        encountered = set()
        encountered_intersection = encountered.intersection
        encountered_update = encountered.update

        # Nodes at the start or end of a way AND nodes that are shared
        # between two or more ways.
        intersections = set()
        intersections_update = intersections.update

        routable_types = set(Street.routable_types)
        bicycle_allowed_types = set(Street.bicycle_allowed_types)

        for el in self.iter_ways('highways.json'):
            tags = el.get('tags')
            get_tag = tags.get
            if tags:
                highway = get_tag('highway')
                bicycle = get_tag('bicycle')
            else:
                highway = None
                bicycle = None
            if not (highway in routable_types or bicycle in bicycle_allowed_types):
                continue
            node_ids = el['nodes']
            intersections_update(
                (node_ids[0], node_ids[-1]),
                encountered_intersection(node_ids),
            )
            encountered_update(node_ids[1:-1])

        return intersections

    @action()
    def process_nodes(self, intersections):
        execute = self.session.execute
        rows = []
        append_row = rows.append

        def insert():
            execute(NODE_TABLE.insert(), rows)
            rows.clear()

        execute(NODE_TABLE.delete())
        execute(INTERSECTION_TABLE.delete())

        for el in self.iter_nodes('highways.json'):
            osm_id = el['id']
            latitude = el['lat']
            longitude = el['lon']
            geom = Point(longitude, latitude)
            node = {
                'id': osm_id,
                'is_intersection': osm_id in intersections,
                'geom': geom,
            }
            append_row(node)
            if len(rows) > 500:
                insert()

        if rows:
            insert()

        execute(
            INTERSECTION_TABLE.insert().from_select(
                [INTERSECTION_TABLE.c.id, INTERSECTION_TABLE.c.geom],
                select([NODE_TABLE.c.id, NODE_TABLE.c.geom]).where(NODE_TABLE.c.is_intersection)
            )
        )

    @action()
    def process_ways(self):
        def insert():
            self.session.execute(STREET_TABLE.insert(), rows)
            rows.clear()

        way_id = 0
        rows = []
        empty_tags = {}
        routable_types = set(Street.routable_types)
        bicycle_allowed_types = set(Street.bicycle_allowed_types)
        true_values = {'yes', 'true', '1'}
        bounds = self.bounds
        execute = self.session.execute
        normalize_street_name = self.normalize_street_name
        node_table_select = NODE_TABLE.select
        node_table_id = NODE_TABLE.c.id
        node_table_geom = NODE_TABLE.c.geom
        intersection_table_id = INTERSECTION_TABLE.c.id
        intersection_table_geom = INTERSECTION_TABLE.c.geom

        execute(STREET_TABLE.delete())

        for el in self.iter_ways('highways.json'):
            osm_id = el['id']
            node_ids = el['nodes']
            tags = el.get('tags', empty_tags)
            get_tag = tags.get

            if tags:
                highway = get_tag('highway')
                bicycle = get_tag('bicycle')
                if highway:
                    highway = highway.strip() or None
                if bicycle:
                    bicycle = bicycle.strip() or None
            else:
                highway = None
                bicycle = None

            if not (highway in routable_types or bicycle in bicycle_allowed_types):
                continue

            if tags:
                name = get_tag('name')
                description = get_tag('description')
                cycleway = get_tag('cycleway')
                oneway = get_tag('oneway')
                oneway_bicycle = get_tag('oneway:bicycle')
                if name:
                    name = normalize_street_name(name)
                if description:
                    description = description.strip() or None
                if cycleway:
                    cycleway = cycleway.strip() or None
                oneway = oneway in true_values
                if oneway_bicycle is not None:
                    oneway_bicycle = oneway_bicycle in true_values
                else:
                    oneway_bicycle = oneway
            else:
                name = None
                description = None
                cycleway = None
                oneway = False
                oneway_bicycle = False

            # Get all nodes for way (in order).
            node_q = node_table_select()
            node_q = node_q.where(node_table_id.in_(node_ids))
            node_map = {n.id: n for n in execute(node_q)}
            nodes = [node_map[i] for i in node_ids]

            # Split way into multiple ways on intersection nodes.
            # Necessary because OSM ways can span multiple real-world
            # street segments.
            ways = []
            way_nodes = [nodes[0]]
            for node in nodes[1:]:
                way_nodes.append(node)
                if node.is_intersection:
                    ways.append(way_nodes)
                    way_nodes = [node]

            # If a way leaves the bounding box, split it up into
            # sub-ways that are all inside the bounding box.
            bounded_ways = []
            delete_intersections = []
            insert_intersections = []
            for way in ways:
                nodes = []
                for node in way:
                    if bounds.contains(node.geom):
                        nodes.append(node)
                    else:
                        nodes.append(None)
                        delete_intersections.append(node)
                if all(nodes):
                    bounded_ways.append(way)
                else:
                    bounded_way = []
                    for node, next_node in zip(nodes, chain(nodes[1:], [None])):
                        if node is None:
                            continue
                        bounded_way.append(node)
                        if next_node is None and len(bounded_way) > 1:
                            start_node_id = bounded_way[0]
                            end_node_id = bounded_way[-1]
                            bounded_ways.append(bounded_way)
                            insert_intersections.extend((start_node_id, end_node_id))
                            bounded_way = []
            if delete_intersections:
                node_ids = (node.id for node in delete_intersections)
                execute(
                    INTERSECTION_TABLE
                        .delete()
                        .where(intersection_table_id.in_(node_ids))
                )
            if insert_intersections:
                node_ids = tuple(node.id for node in insert_intersections)
                execute(
                    pg_insert(INTERSECTION_TABLE)
                        .from_select(
                            [intersection_table_id, intersection_table_geom],
                            select([node_table_id, node_table_geom])
                                .where(node_table_id.in_(node_ids))
                        )
                        .on_conflict_do_nothing(index_elements=[intersection_table_id])
                )

            for i, way in enumerate(bounded_ways):
                way_id += 1
                start_node_id = way[0].id
                end_node_id = way[-1].id
                geom = LineString((n.geom.coords[0] for n in way))
                attrs = {
                    'id': way_id,
                    'osm_id': osm_id,
                    'osm_seq': i,
                    'geom': geom,
                    'start_node_id': start_node_id,
                    'end_node_id': end_node_id,
                    'name': name,
                    'description': description,
                    'highway': highway,
                    'bicycle': bicycle,
                    'cycleway': cycleway,
                    'oneway': oneway,
                    'oneway_bicycle': oneway_bicycle,
                }
                attrs['base_cost'] = base_cost(**attrs)
                rows.append(attrs)

            if len(rows) > 500:
                insert()

        if rows:
            insert()

    @action()
    def drop_node_table(self):
        """Drop temporary node table"""
        NODE_TABLE.drop(self.session.connection(), checkfirst=True)

    @action()
    def create_graph(self):
        """Create graph"""
        builder = OSMGraphBuilder(self.graph_path, session=self.session, quiet=True)
        builder.run()

    @action()
    def drop_place_tables(self):
        # TODO:
        # tables = ()
        # Base.metadata.drop_all(self.session.connection(), tables=tables)
        pass

    @action()
    def create_place_tables(self):
        # TODO:
        # tables = ()
        # Base.metadata.create_all(self.session.connection(), tables=tables)
        pass

    @action
    def process_places(self):
        # TODO:
        pass

    def normalize_street_name(self, name):
        name = name.strip()

        if not name:
            return None

        parts = name.split()

        if len(parts) == 1:
            return parts[0]

        prefix, *rest = parts
        normalized_parts = []

        prefix_lower = prefix.lower()
        if prefix_lower in directions_ftoa:
            # Abbreviate prefix
            prefix = directions_ftoa[prefix_lower].upper()
            normalized_parts.append(prefix)
        else:
            rest = parts

        if len(rest) == 1:
            name = rest[0]
            normalized_parts.append(name)
        else:
            *name, suffix = rest
            suffix_lower = suffix.lower()

            if suffix_lower in directions_ftoa:
                # Ends with a direction
                suffix = directions_ftoa[suffix_lower].upper()

                # Check for street type before direction
                if len(name) > 1:
                    *name, street_type = name
                    street_type_lower = street_type.lower()
                    if street_type_lower in self.street_type_map:
                        street_type = self.street_type_map[street_type_lower]
                        street_type = street_type.capitalize()
                        suffix = ' '.join((street_type, suffix))
                    else:
                        name = name + [street_type]
            elif suffix_lower in self.street_type_map:
                # Ends with a street type
                suffix = self.street_type_map[suffix_lower].capitalize()

            normalized_parts.extend(name)
            normalized_parts.append(suffix)

        name = ' '.join(normalized_parts)
        return name

    def vacuum(self, *tables):
        """Vacuum ``tables`` or all tables if ``tables`` aren't specified."""
        connection = self.engine.raw_connection()
        connection.set_isolation_level(0)
        with connection.cursor() as cursor:
            if not tables:
                cursor.execute('VACUUM FULL ANALYZE')
            else:
                for table in tables:
                    cursor.execute('VACUUM FULL ANALYZE {}'.format(table))
        connection.set_isolation_level(2)
        connection.close()
