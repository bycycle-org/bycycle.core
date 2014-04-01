from dijkstar import Graph

from sqlalchemy import create_engine

from bycycle.core.model import Street
from bycycle.core.util import Timer


class OSMGraphBuilder:

    def __init__(self, file_name, db_url):
        self.file_name = file_name
        self.engine = create_engine(db_url)
        self.graph = Graph()

    def run(self):
        timer = Timer()
        timer.start()

        graph = self.graph
        q = Street.__table__.select()
        result = self.engine.execute(q)
        num_rows = result.rowcount
        template = '\rBuilding graph from {} streets... {{:.0%}}'
        template = template.format(num_rows)
        print(template.format(0), end='')
        for i, r in enumerate(result):
            edge = (
                r.id,
                r.geom.length,
                r.name,
                r.highway,
                r.bicycle,
                r.cycleway,
            )
            graph.add_edge(r.start_node_id, r.end_node_id, edge)
            if r.oneway_bicycle:
                # Ensure end node is in graph; this is relevant for one
                # way streets near the boundary of the graph.
                if r.end_node_id not in graph:
                    graph.add_node(r.end_node_id)
            else:
                graph.add_edge(r.end_node_id, r.start_node_id, edge)
            print(template.format(i / num_rows), end='')
        timer.stop()
        print(template.format(1), timer)

        timer.start()
        print('Writing graph to disk... ', end='')
        graph.marshal(self.file_name)
        print('Done', timer)
        timer.stop()
