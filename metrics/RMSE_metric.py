from .base import IMetric
import networkx as nx

class RMSEMetric(IMetric):

    @property
    def name(self) -> str:
        return "rmse"

    def evaluate(self, graph: nx.Graph, **parameters) -> float:
        rss = 0
        count = 0

        for p1, p2, orig_dist in graph.edges(data="orig_dist"):
            rss += self._rss(graph.nodes[p1]["pos"], graph.nodes[p2]["pos"], orig_dist)
            count += 1

        return (rss / count) ** 0.5

    def _rss(self, p1, p2, orig_dist) -> float:
        x1, y1 = p1
        x2, y2 = p2
        curr_dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        return (curr_dist - orig_dist) ** 2
