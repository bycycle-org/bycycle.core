from pathlib import Path

import dijkstar

from bycycle.core.model import get_engine, get_session_factory, Street
from bycycle.core.util import Timer


class OSMGraphBuilder:

    """Build graph and save to disk.

    Args:
        path: Path to save graph to
        connection_args: A dictionary containing SQLAlchemy connection
            arguments (can be omitted if a ``session`` is passed)
        session: An existing SQLAlchemy session to use

    """

    def __init__(self, path, connection_args=None, session=None, quiet=False):
        self.path = Path(path).resolve()
        self.quiet = quiet

        if session:
            self.session = session
        else:
            engine = get_engine(**connection_args)
            session_factory = session or get_session_factory(engine)
            self.session = session_factory()

        self.engine = self.session.bind

    def run(self):
        quiet = self.quiet
        graph = dijkstar.Graph()
        q = Street.__table__.select()
        result = self.session.execute(q)
        num_rows = result.rowcount

        if not quiet:
            timer = Timer()
            timer.start()
            template = '\rBuilding graph from {} streets... {{:.0%}}'
            template = template.format(num_rows)
            print(template.format(0), end='')

        for i, r in enumerate(result):
            edge = (r.id, r.base_cost, r.name or r.description)
            graph.add_edge(r.start_node_id, r.end_node_id, edge)
            if not r.oneway_bicycle:
                graph.add_edge(r.end_node_id, r.start_node_id, edge)
            if not quiet:
                print(template.format(i / num_rows), end='')

        if not quiet:
            timer.stop()
            print(template.format(1), timer)
            timer.start()

        if not quiet:
            print(f'Saving graph to {self.path}... ', end='', flush=True)

        graph.marshal(str(self.path))

        if not quiet:
            print('Done', timer)
            timer.stop()
