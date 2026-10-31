from .base import IMetric
import networkx as nx

class CrossingEdgesMetric(IMetric):

    @property
    def name(self) -> str:
        return "crossing_edges"

    def evaluate(self, graph: nx.Graph) -> float:
        crossing_count = 0
        edges = list(graph.edges)
        positions = nx.get_node_attributes(graph, "pos")

        for i in range(len(edges)):
            for j in range(i + 1, len(edges)):
                edge1 = edges[i]
                edge2 = edges[j]

                if self._edges_cross(edge1, edge2, positions):
                    crossing_count += 1

        return float(crossing_count)

    def _cross(self, a, b):
        return a[0] * b[1] - a[1] * b[0]


    def _orient(self, a, b, c):
        return self._cross(
            (b[0] - a[0], b[1] - a[1]),
            (c[0] - a[0], c[1] - a[1])
        )


    def _proper_inter(self, p1, p2, p3, p4):
        oa = self._orient(p3, p4, p1)
        ob = self._orient(p3, p4, p2)
        oc = self._orient(p1, p2, p3)
        od = self._orient(p1, p2, p4)

        # Proper intersection exists iff opposite signs
        return oa * ob < 0 and oc * od < 0

    def _edges_cross(self, edge1, edge2, positions) -> bool:
        p1 = positions[edge1[0]]
        p2 = positions[edge1[1]]
        p3 = positions[edge2[0]]
        p4 = positions[edge2[1]]

        return self._proper_inter(p1, p2, p3, p4)

        a1x, a1y = p1
        b1x, b1y = p2
        a2x, a2y = p3
        b2x, b2y = p4

        v1x = b1x - a1x
        v1y = b1y - a1y
        v2x = b2x - a2x
        v2y = b2y - a2y

        s = (v1x * (a1y - a2y) + v1y * (a2x - a1x)) / (v1x * v2y - v1y * v2x)

        if s <= 0 or s >= 1:
            return False

        return True
        