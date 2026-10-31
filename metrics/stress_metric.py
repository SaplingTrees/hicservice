from .base import IMetric
import networkx as nx

class StressMetric(IMetric):

    @property
    def name(self) -> str:
        return "stress"

    # Now we compare the original distance with the current one
    # only for edges that exist in the graph.

    # It could be potentially useful to consider all pairs of nodes,
    # leading to different stress values for the same graph layout, but we will stick to edges for now.
    def evaluate(self, graph: nx.Graph) -> float:
        total_stress = 0

        for p1, p2, orig_dist in graph.edges(data="orig_dist"):
            total_stress += self._stress(graph.nodes[p1]["pos"], graph.nodes[p2]["pos"], orig_dist)

        return total_stress

    def _stress(self, p1, p2, orig_dist) -> float:
        x1, y1 = p1
        x2, y2 = p2
        curr_dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        return (curr_dist - orig_dist) ** 2
