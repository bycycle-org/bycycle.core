from pathlib import Path

import dijkstar

from bycycle.core import models
from bycycle.core.util import Timer


class OSMGraphBuilder:
    """Build graph and save to disk.

    Args:
        path: Path to save graph to

    """

    def __init__(self, path, quiet=False):
        self.path = Path(path).resolve()
        self.quiet = quiet

    def run(self):
        loud = not self.quiet
        timer = Timer()
        template = "\rBuilding graph from {} streets... {{:.1%}}"

        if loud:
            timer.start()

        graph = dijkstar.Graph()
        num_rows = models.Street.objects.count()

        if loud:
            template = template.format(f"{num_rows:,}")
            print(template.format(0), end="")

        q = models.Street.objects.order_by("id")
        chunk_size = 1000
        last_id = 0
        num_processed = 0
        while num_processed < num_rows:
            count = 0
            for i, r in enumerate(q.filter(id__gt=last_id)[:chunk_size]):
                count += 1
                num_processed += 1
                edge = (r.id, r.base_cost, r.name or r.description)
                graph.add_edge(r.start_node.id, r.end_node.id, edge)
                if not r.oneway_bicycle:
                    graph.add_edge(r.end_node.id, r.start_node.id, edge)
                if loud:
                    print(template.format(num_processed / num_rows), end="")
            if count == 0:
                break

        if loud:
            timer.stop()
            print(template.format(1), timer)
            timer.start()

        if loud:
            print(f"Saving graph to {self.path}... ", end="", flush=True)

        graph.marshal(str(self.path))

        if loud:
            print("Done", timer)
            timer.stop()
