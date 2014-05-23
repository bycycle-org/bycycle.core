from xml.etree import ElementTree

from sqlalchemy import create_engine
from sqlalchemy.sql import select

from tangled.converters import get_converter
from tangled.decorators import reify

from bycycle.core.geometry import LineString, Point
from bycycle.core.model import Base, Intersection, Street, USPSStreetSuffix
from bycycle.core.model.compass import directions_ftoa
from bycycle.core.util import PeriodicRunner, Timer


INTERSECTION_TABLE = Intersection.__table__
STREET_TABLE = Street.__table__
SUFFIX_TABLE = USPSStreetSuffix.__table__


def action(order, description=None):
    def wrapper(meth):
        meth.__action__ = {
            'order': order,
            'description': description,
        }
        return meth
    return wrapper


class Action:

    def __init__(self, meth, order, description=None):
        self.meth = meth
        self.order = order
        if description is not None:
            self.description = description
        elif meth.__doc__:
            self.description = meth.__doc__.strip().split('\n')[0]
        else:
            self.description = meth.__name__.replace('_', ' ')


class OSMImporter:

    """Imports ways and their start and end nodes.

    It's assumed that all of the ways in the input OSM file have a
    non-empty highway tag.

    Ways are split where they share a node with another way.

    Nodes used only for geometry are not inserted--only nodes that are
    at the start and end of a way are.

    ``file_name``
        The OSM file (in XML format) to read from.

    ``db_url``
        A database URL that SQLAlchemy can understand. Typically
        something like 'postgresql://user:password@host/bycycle'.
        For local setups, something like 'postgresql:///bycycle'
        might work.

    ``actions``
        A list of actions to perform. By default (when this isn't
        specified), all actions will be performed.

    """

    def __init__(self, file_name, db_url, actions=None):
        self.file_name = file_name
        self.engine = create_engine(db_url)
        if actions:
            self.actions = [self.all_actions[i - 1] for i in actions]
        else:
            self.actions = self.all_actions

    @reify
    def all_actions(self):
        actions = []
        for name, attr in self.__class__.__dict__.items():
            if hasattr(attr, '__action__'):
                meth = getattr(self, name)
                order = attr.__action__['order']
                description = attr.__action__['description']
                actions.append(Action(meth, order, description))
        actions.sort(key=lambda a: a.order)
        return actions

    @reify
    def street_type_map(self):
        street_type_map = {}
        for r in self.engine.execute(SUFFIX_TABLE.select()):
            street_type_map[r.name] = r.abbreviation
            street_type_map[r.alias] = r.abbreviation
        return street_type_map

    def run(self):
        result = None
        template = '\r{0.order}. {0.description}... {1}'
        action_timer = Timer()
        total_timer = Timer()
        total_timer.start()
        runner_threads = []
        status = lambda a, t: print(template.format(a, t), end='')
        try:
            for a in self.actions:
                with action_timer:
                    print(template.format(a, action_timer), end='')
                    runner = PeriodicRunner(
                        target=status, args=(a, action_timer), interval=0.2)
                    runner_threads.append(runner)
                    runner.start()
                    if result is not None:
                        result = a.meth(result)
                    else:
                        result = a.meth()
                    runner.stop()
                    runner.join()
                    print(template.format(a, action_timer))
        except KeyboardInterrupt:
            for r in runner_threads:
                r.stop()
            print('\nAborted')
        except Exception as exc:
            for r in runner_threads:
                r.stop()
            raise exc
        else:
            total_timer.stop()
            print('Total time: {}'.format(total_timer))

    @action(1)
    def drop_tables(self):
        """Drop tables"""
        tables = (INTERSECTION_TABLE, STREET_TABLE)
        Base.metadata.drop_all(self.engine, tables=tables)

    @action(2)
    def create_tables(self):
        """Create tables"""
        tables = (INTERSECTION_TABLE, STREET_TABLE)
        Base.metadata.create_all(self.engine, tables=tables)

    @action(3)
    def process_nodes(self):
        """Process nodes"""
        # All the nodes encountered so far.
        encountered = set()

        # Nodes at the start or end of a way AND nodes that are shared
        # between two or more ways. These will be inserted into the DB.
        intersections = set()

        # Go through all the ways and find all the intersection nodes.
        for event, el in ElementTree.iterparse(self.file_name):
            if el.tag == 'way':
                node_ids = [int(n.get('ref')) for n in el.iterfind('nd')]
                el.clear()
                # This is necessary in case a start or end node isn't shared
                # with any other ways. E.g., at a dead end or at the data
                # boundary.
                encountered |= {node_ids[0], node_ids[-1]}
                for node_id in node_ids:
                    if node_id in encountered:
                        intersections.add(node_id)
                    else:
                        encountered.add(node_id)
            elif el.tag in ('node', 'ref'):
                el.clear()

        del encountered

        rows = []

        def insert():
            self.engine.execute(INTERSECTION_TABLE.insert(), rows)
            rows.clear()

        self.engine.execute(INTERSECTION_TABLE.delete())

        for osm_id, node in self.iter_nodes():
            if osm_id in intersections:
                rows.append(node)
            if len(rows) > 1000:
                insert()

        if rows:
            insert()

    @action(4)
    def process_ways(self):
        """Process ways"""
        all_nodes = {osm_id: node for (osm_id, node) in self.iter_nodes()}

        get_tag = self.get_tag
        normalize_street_name = self.normalize_street_name

        bool_converter = get_converter('bool')

        # TODO: Change oneway from bool to (-1, 0, 1)?
        #        0 => not a one way
        #        1 => one way in node order
        #       -1 => one way in reverse node order
        def oneway_converter(v):
            try:
                return bool_converter(v)
            except ValueError:
                return True

        result = self.engine.execute(select([INTERSECTION_TABLE.c.id]))
        intersection_ids = set(r.id for r in result)

        way_id = 0
        rows = []

        def insert():
            self.engine.execute(STREET_TABLE.insert(), rows)
            rows.clear()

        self.engine.execute(STREET_TABLE.delete())

        for event, el in ElementTree.iterparse(self.file_name):
            if el.tag == 'way':
                osm_id = int(el.get('id'))
                node_ids = [int(n.get('ref')) for n in el.iterfind('nd')]

                name = get_tag(el, 'name', normalize_street_name)
                highway = get_tag(el, 'highway')
                bicycle = get_tag(el, 'bicycle')
                cycleway = get_tag(el, 'cycleway')
                foot = get_tag(el, 'foot')
                sidewalk = get_tag(el, 'sidewalk')

                oneway = get_tag(el, 'oneway', oneway_converter, False)
                oneway_bicycle = get_tag(el, 'oneway:bicycle', oneway_converter)
                if oneway_bicycle is None:
                    oneway_bicycle = get_tag(el, 'bicycle:oneway', oneway_converter)
                    if oneway_bicycle is None:
                        oneway_bicycle = oneway

                el.clear()

                way = []
                ways = []
                nodes = [all_nodes[node_id] for node_id in node_ids]
                last_i = len(nodes) - 1
                for i, node in enumerate(nodes):
                    way.append(node)
                    if len(way) > 1 and node['id'] in intersection_ids:
                        ways.append(way)
                        if i < last_i:
                            way = [node]

                for i, way in enumerate(ways):
                    way_id += 1
                    start_node_id = way[0]['id']
                    end_node_id = way[-1]['id']
                    geom = LineString((n['geom'].coords[0] for n in way))
                    lat_long = LineString((n['lat_long'].coords[0] for n in way))
                    rows.append({
                        'id': way_id,
                        'osm_id': osm_id,
                        'osm_seq': i,
                        'geom': geom,
                        'lat_long': lat_long,
                        'start_node_id': start_node_id,
                        'end_node_id': end_node_id,
                        'name': name,
                        'highway': highway,
                        'bicycle': bicycle,
                        'cycleway': cycleway,
                        'foot': foot,
                        'sidewalk': sidewalk,
                        'oneway': oneway,
                        'oneway_bicycle': oneway_bicycle,
                    })

                if len(rows) > 1000:
                    insert()
            elif el.tag in ('node', 'ref'):
                el.clear()

        if rows:
            insert()

    @action(5)
    def vacuum_tables(self):
        """Vacuum tables"""
        self.vacuum(INTERSECTION_TABLE, STREET_TABLE)

    def iter_nodes(self):
        for event, el in ElementTree.iterparse(self.file_name):
            if el.tag == 'node':
                osm_id = int(el.get('id'))
                latitude = float(el.get('lat'))
                longitude = float(el.get('lon'))
                lat_long = Point(longitude, latitude)
                geom = lat_long.reproject()
                node = {
                    'id': osm_id,
                    'geom': geom,
                    'lat_long': lat_long,
                }
                yield osm_id, node
            el.clear()

    @staticmethod
    def get_tag(el, tag, converter=None, default=None):
        tag_el = el.find('tag[@k="{}"]'.format(tag))
        if tag_el is None:
            return default
        else:
            v = tag_el.get('v')
            if not v.strip():
                return default
            if converter:
                v = converter(v)
            return v

    def normalize_street_name(self, name):
        if name is None:
            return None

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
            rest = [prefix] + rest

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
