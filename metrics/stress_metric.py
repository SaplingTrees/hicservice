from .base import IMetric
import networkx as nx

class StressMetric(IMetric):

    @property
    def name(self) -> str:
        return "stress"

    __weight_options = [
        "uniform",
        "inverse_distance_squared",
    ]

    __node_selection_options = [
        "edges",
        "available_pairs"
    ]

    # Now we compare the original distance with the current one
    # only for edges that exist in the graph.

    # It could be potentially useful to consider all pairs of nodes,
    # leading to different stress values for the same graph layout, but we will stick to edges for now.

    # The stress metric generally also requires a weight for each pair of nodes,
    # but since we do not pass weights into the graph / evaluator we now
    # assume all weights to be equal to 1.0
    def evaluate(self, graph: nx.Graph, **parameters) -> float:
        normalize: bool = parameters.get("normalize", False)
        weighting = parameters.get("weighting", self.__weight_options[0])
        selection = parameters.get("selection", self.__node_selection_options[0])

        if (weighting not in self.__weight_options):
            weighting = self.__weight_options[0]

        if (selection not in self.__node_selection_options):
            selection = self.__node_selection_options[0]

        result, norm_term = (0.0, 1.0)

        if (selection == "edges"):
            result, norm_term = self._evaluate_edge_stress(graph, weighting, normalize)
        elif (selection == "available_pairs"):
            result, norm_term = self._evaluate_edge_stress(graph, weighting, normalize)

        if (normalize):
            result = (result / norm_term) ** 0.5

        return result

    def _get_weight(self, weighting, orig_dist) -> float:
        if (weighting == "uniform"):
            return 1.0

        elif (weighting == "inverse_distance_squared"):
            return 1.0 / (orig_dist * orig_dist)

        return 0.0

    def _evaluate_edge_stress(self, graph: nx.Graph, weighting, calculate_normalization: bool) -> float:
        total_stress = 0
        norm = 1.0

        if (calculate_normalization):
            norm = 0.0

        for p1, p2, orig_dist in graph.edges(data="orig_dist"):
            weight = self._get_weight(weighting, orig_dist)

            if (calculate_normalization):
                norm += self._norm(orig_dist, weight)

            total_stress += self._stress(graph.nodes[p1]["pos"], graph.nodes[p2]["pos"], orig_dist, weight)

        return (total_stress, norm)

    def _norm(self, orig_dist, weight) -> float:
        return orig_dist * orig_dist * weight

    def _stress(self, p1, p2, orig_dist, weight) -> float:
        x1, y1 = p1
        x2, y2 = p2
        curr_dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        return weight * ((curr_dist - orig_dist) ** 2)
