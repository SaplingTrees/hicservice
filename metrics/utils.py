import networkx as nx
from typing import Tuple, List
from numpy import hypot

# Requires graph to have orig_dist defined per edge
# returns pair (layout_distances, original_distances)
def get_distances_pair(graph: nx.graph) -> Tuple[List[float], List[float]]:
    original_distances = []
    layout_distances = []

    for u, v, orig_dist in graph.edges(data="orig_dist"):

        original_distances.append(orig_dist)

        x1, y1 = graph.nodes[u]["pos"]
        x2, y2 = graph.nodes[v]["pos"]

        layout_distance = hypot(x2 - x1, y2 - y1)
        layout_distances.append(layout_distance)

    return (layout_distances, original_distances)
