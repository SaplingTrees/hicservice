from .base import IMetric
import networkx as nx

class EdgeCountMetric(IMetric):

    @property
    def name(self) -> str:
        return "edge_count"

    def evaluate(self, graph: nx.Graph) -> float:
        return float(graph.number_of_edges())

class OrigDistSumMetric(IMetric):

    @property
    def name(self) -> str:
        return "orig_dist_sum"

    def evaluate(self, graph: nx.Graph) -> float:
        sum = 0
        distances = nx.get_edge_attributes(graph, "orig_dist")

        for e in graph.edges:
            sum += distances[e]

        return sum
