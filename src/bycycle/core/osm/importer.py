from functools import cached_property
from itertools import chain
from pathlib import Path

import ijson
from shapely.geometry import Polygon

from bycycle.core import models
from bycycle.core.geometry import DEFAULT_SRID, LineString, Point
from bycycle.core.models.compass import directions_ftoa
from bycycle.core.models.street import base_cost
from bycycle.core.util import PeriodicRunner, Timer

from .graph import OSMGraphBuilder


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
            self.description = meth.__doc__.strip().split("\n")[0]
        else:
            self.description = meth.__name__.replace("_", " ").capitalize()

    def __str__(self):
        return f"{self.order}: {self.description}"


class OSMImporter:
    """Imports ways and their start and end nodes.

    It's assumed that all the ways in the input OSM file have a
    non-empty highway tag.

    Ways are split where they share a node with another way.

    Nodes used only for geometry are not inserted--only nodes that are
    at the start and end of a way are.

    Args:
        bbox (tuple): Bounding box
        data_directory: Directory containing OSM data files
        graph_path: Path to save graph to
        actions: A list of actions to perform. By default, all actions
            will be performed

    """

    def __init__(
        self,
        bbox,
        data_directory,
        graph_path,
        streets=True,
        places=True,
        actions=None,
    ):
        self.bbox = bbox
        self.bounds = Polygon.from_bounds(*bbox)
        self.data_directory = Path(data_directory).resolve()
        self.graph_path = graph_path

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
            items = ijson.items(fp, "elements.item")
            for item in items:
                if item["type"] == "node":
                    yield item

    def iter_ways(self, file_name):
        path = self.data_directory / file_name
        with path.open() as fp:
            items = ijson.items(fp, "elements.item")
            for item in items:
                if item["type"] == "way":
                    yield item

    @cached_property
    def all_actions(self):
        actions = [
            attr.__action__
            for attr in self.__class__.__dict__.values()
            if hasattr(attr, "__action__")
        ]
        actions.sort(key=lambda act: act.order)
        return actions

    @cached_property
    def street_type_map(self):
        street_type_map = {}
        for row in models.USPSStreetSuffix.objects.all():
            street_type_map[row.name] = row.abbreviation
            street_type_map[row.alias] = row.abbreviation
        return street_type_map

    def run(self):
        result = None
        action_timer = Timer()
        total_timer = Timer()
        total_timer.start()

        def status(for_action, timer, end=""):
            message = "\r{action.order}. {action.description}... {timer}"
            message = message.format(action=for_action, timer=timer)
            print(" " * (len(message) + 20), message, sep="", end=end)

        try:
            for current_action in self.actions:
                with action_timer:
                    status(current_action, action_timer)
                    runner = PeriodicRunner(
                        target=status,
                        args=(current_action, action_timer),
                        interval=0.2,
                    )
                    runner.start()
                    if result is not None:
                        result = current_action.meth(self, result)
                    else:
                        result = current_action.meth(self)
                    runner.stop()
                    runner.join()
                    status(current_action, action_timer, end="\n")
        except KeyboardInterrupt:
            runner.stop()
            runner.join()
            print("\nAborted")
        except Exception as exc:
            runner.stop()
            runner.join()
            raise exc
        else:
            total_timer.stop()
            print("Total time: {}".format(total_timer))

        print("Vacuuming tables...", end=" ", flush=True)
        self.vacuum(models.Intersection, models.Street)
        print("Done")

    @action()
    def clear_street_tables(self):
        models.OsmNode.objects.all().delete()
        models.Intersection.objects.all().delete()
        models.Street.objects.all().delete()

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

        routable_types = set(models.Street.routable_types)
        bicycle_allowed_types = set(models.Street.bicycle_allowed_types)

        for el in self.iter_ways("highways.json"):
            tags = el.get("tags")
            get_tag = tags.get
            if tags:
                highway = get_tag("highway")
                bicycle = get_tag("bicycle")
            else:
                highway = None
                bicycle = None
            if not (highway in routable_types or bicycle in bicycle_allowed_types):
                continue
            node_ids = el["nodes"]
            intersections_update(
                (node_ids[0], node_ids[-1]),
                encountered_intersection(node_ids),
            )
            encountered_update(node_ids[1:-1])

        return intersections

    @action()
    def process_nodes(self, intersections):
        def insert_nodes():
            models.OsmNode.objects.bulk_create(node_rows)
            node_rows.clear()

        def insert_intersections():
            models.Intersection.objects.bulk_create(intersection_rows)
            intersection_rows.clear()

        node_rows = []
        append_node = node_rows.append

        intersection_rows = []
        append_intersection = intersection_rows.append

        models.OsmNode.objects.all().delete()
        models.Intersection.objects.all().delete()

        for el in self.iter_nodes("highways.json"):
            osm_id = el["id"]
            latitude = el["lat"]
            longitude = el["lon"]
            is_intersection = osm_id in intersections
            point = Point(longitude, latitude)
            geom = point.as_geos()
            append_node(models.OsmNode(osm_id, is_intersection, geom))
            if len(node_rows) > 1000:
                insert_nodes()

        if node_rows:
            insert_nodes()

        for node in models.OsmNode.objects.filter(is_intersection=True):
            append_intersection(models.Intersection(node.id, node.geom))
            if len(intersection_rows) > 1000:
                insert_intersections()

        if intersection_rows:
            insert_intersections()

    @action()
    def process_ways(self):
        def insert():
            models.Street.objects.bulk_create(rows)
            rows.clear()

        way_id = 0
        rows = []
        empty_tags = {}
        routable_types = set(models.Street.routable_types)
        bicycle_allowed_types = set(models.Street.bicycle_allowed_types)
        true_values = {"yes", "true", "1"}
        bounds = self.bounds
        normalize_street_name = self.normalize_street_name

        models.Street.objects.all().delete()

        for el in self.iter_ways("highways.json"):
            osm_id = el["id"]
            node_ids = el["nodes"]
            tags = el.get("tags", empty_tags)
            get_tag = tags.get

            if tags:
                highway = get_tag("highway")
                bicycle = get_tag("bicycle")
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
                name = get_tag("name")
                description = get_tag("description")
                cycleway = get_tag("cycleway")
                oneway = get_tag("oneway")
                oneway_bicycle = get_tag("oneway:bicycle")
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
            node_q = models.OsmNode.objects.filter(id__in=node_ids)
            node_map = {n.id: n for n in node_q}
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
                    if bounds.contains(Point(node.geom.x, node.geom.y)):
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
                models.Intersection.objects.filter(id__in=node_ids).delete()

            if insert_intersections:
                node_ids = tuple(node.id for node in insert_intersections)
                intersections = (
                    models.Intersection(node.id, node.geom)
                    for node in models.OsmNode.objects.filter(id__in=node_ids)
                )
                models.Intersection.objects.bulk_create(
                    intersections, ignore_conflicts=True
                )

            for i, way in enumerate(bounded_ways):
                way_id += 1
                start_node_id = way[0].id
                end_node_id = way[-1].id
                line = LineString(((n.geom.x, n.geom.y) for n in way))
                geom = line.as_geos()
                attrs = {
                    "id": way_id,
                    "osm_id": osm_id,
                    "osm_seq": i,
                    "geom": geom,
                    "start_node_id": start_node_id,
                    "end_node_id": end_node_id,
                    "name": name,
                    "description": description,
                    "highway": highway,
                    "bicycle": bicycle,
                    "cycleway": cycleway,
                    "oneway": oneway,
                    "oneway_bicycle": oneway_bicycle,
                }
                attrs["base_cost"] = base_cost(**attrs)
                rows.append(models.Street(**attrs))

            if len(rows) > 500:
                insert()

        if rows:
            insert()

    @action()
    def create_graph(self):
        """Create graph"""
        builder = OSMGraphBuilder(self.graph_path, quiet=True)
        builder.run()

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
                        suffix = " ".join((street_type, suffix))
                    else:
                        name = name + [street_type]
            elif suffix_lower in self.street_type_map:
                # Ends with a street type
                suffix = self.street_type_map[suffix_lower].capitalize()

            normalized_parts.extend(name)
            normalized_parts.append(suffix)

        name = " ".join(normalized_parts)
        return name

    def vacuum(self, *models):
        """Vacuum ``tables`` or all tables if ``tables`` aren't specified."""
        for model in models:
            model.objects.raw(f"VACUUM FULL ANALYZE {model}")
