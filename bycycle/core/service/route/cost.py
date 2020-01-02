import sys


def cost_func(u, v, edge, prev_edge):
    _, cost, name = edge
    if cost is None:
        return sys.maxsize
    if prev_edge:
        # Add penalty for:
        #   - streets with no name
        #   - turning onto a street with a different name
        prev_name = prev_edge[2]
        if not name or name != prev_name:
            cost *= 2
    return cost
