class TravelMode(object):

    def getEdgeWeight(self, v, edge_attrs, prev_edge_attrs):
        length = edge_attrs[self.indices['length']]
        return length

    getHeuristicWeight = None
