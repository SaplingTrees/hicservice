from .base import IMetric
import networkx as nx
from scipy import stats
import numpy as np
from .utils import get_distances_pair

class SpearmanCorrelationCoefficientMetric(IMetric):

    @property
    def name(self) -> str:
        return "spearman_cc"

    def evaluate(self, graph: nx.Graph, **parameters) -> float:
        layout_distances, original_distances = get_distances_pair(graph)

        if len(original_distances) < 2:
            raise ValueError("At least two edges are required.")

        result = stats.spearmanr(
            original_distances,
            layout_distances
        )

        if not np.isfinite(result.statistic):
            raise ValueError("Pearson correlation is undefined.")

        return float(result.statistic)