import io

import dijkstar

from bycycle.core.geometry import DEFAULT_SRID
from bycycle.core.model import get_engine, get_session_factory, Graph, Street
from bycycle.core.util import Timer


class OSMGraphBuilder:

    def __init__(self, connection_args, clean=True):
        self.engine = get_engine(**connection_args)
        self.session_factory = get_session_factory(self.engine)
        self.clean = clean

    def run(self):
        timer = Timer()
        timer.start()

        graph = dijkstar.Graph()

        q = Street.__table__.select()
        result = self.engine.execute(q)
        num_rows = result.rowcount

        template = '\rBuilding graph from {} streets... {{:.0%}}'
        template = template.format(num_rows)
        print(template.format(0), end='')

        for i, r in enumerate(result):
            edge = (
                r.id,
                r.geom.reproject(DEFAULT_SRID, 2913).length,
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

        session = self.session_factory()

        if self.clean:
            print('Removing previous graphs...', end='')
            count = session.query(Graph).delete()
            print('Removed', count, 'previous graph%s' % ('' if count == 1 else 's'))

        timer.start()
        print('Saving graph to database... ', end='')

        file = io.BytesIO()
        graph.marshal(file)
        file.seek(0)
        session.add(Graph(data=file.getvalue()))
        session.commit()

        print('Done', timer)
        timer.stop()
