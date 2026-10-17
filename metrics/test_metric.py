from .base import IMetric
import networkx as nx

class EdgeCountMetric(IMetric):

    @property
    def name(self) -> str:
        return "edge_count"

    def evaluate(self, graph: nx.Graph) -> float:
        return float(graph.number_of_edges())
    