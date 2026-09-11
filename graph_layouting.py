import numpy as np
from math import cbrt
from typing import Optional

import networkx as nx;
from networkx.drawing.nx_pydot import graphviz_layout
from sklearn.manifold import MDS

def distance_function(frequency: float) -> float:
    return 1 / cbrt(frequency)

# Returns TRUE is frequency IS filtered
def frequency_filter(frequency: float, threshold: float) -> bool:
    return np.isnan(frequency) or frequency <= threshold

# Returns TRUE is distance IS filtered
def distance_filter(distance: float, threshold: Optional[float]) -> bool:
    return threshold is not None and distance >= threshold

def compute_graph_layout(matrix: np.array, type: str, infer_distances=True, freq_filter=0.0, dist_filter=None, mod_distance=1, mod_weight=2):
    print("Freq:", freq_filter, "Dist:", dist_filter, "Weight:", mod_weight)

    G = nx.Graph()
    measured_distances = {}
    kamada_distances = {}
    n = matrix.shape[0]

    for i in range(n):
        for j in range(i + 1, n):
            frequency = matrix[i, j]

            if frequency_filter(frequency, freq_filter):
                continue
            distance = distance_function(frequency)
            
            if distance_filter(distance, dist_filter):
                continue
            G.add_node(i)
            G.add_node(j)

            if abs(j - i) <= mod_distance:
                distance /= mod_weight
            G.add_edge(i, j, weight=frequency, distance=distance, neighbouring=(i + 1 == j), len=distance)
            bin1dict = measured_distances.setdefault(i, {})
            bin1dict[j] = distance
            kamadabinDict1 = kamada_distances.setdefault(i, {i : 0})
            kamadabinDict1[j] = distance
            kamadabinDict2 = kamada_distances.setdefault(j, {j : 0})
            kamadabinDict2[i] = distance

    if infer_distances:
        dist = dict(nx.all_pairs_dijkstra_path_length(G, weight="distance"))
        nodes = list(G.nodes())

        for i, u in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                v = nodes[j]
                # Skip if edge already exists
                if G.has_edge(u, v):
                    continue
                
                # Check if reachable
                if v in dist[u]:
                    shortest = dist[u][v]

                    if not distance_filter(shortest, dist_filter):
                        continue
                    bin1dict = kamada_distances.setdefault(i, {i : 0})
                    bin1dict[j] = shortest
                    bin2dict = kamada_distances.setdefault(j, {j : 0})
                    bin2dict[i] = shortest
                    # Add new edge with computed distance
                    G.add_edge(u, v, distance=shortest, weight=shortest ** 3, len=shortest, neighbouring=(u + 1 == v or v + 1 == u))

    match type:
        case "kamada":
            return nx.kamada_kawai_layout(G, dist=kamada_distances, weight='distance')
        # Spring is Frucherman Reingold
        case "spring":
            return nx.spring_layout(G)
        case "forceatlas2":
            result = nx.forceatlas2_layout(G, weight='distance')
            return {node: pos.tolist() for node, pos in result.items()}
        # Stresful is Stress majorization
        case "stressful":
            return graphviz_layout(G, prog="neato")
        case "mds":
            return compute_mds(G)
        case _:
            raise ValueError("Layout type " + type + " is not supported.")
        

def compute_mds(G):
    nodes = list(G.nodes())
    n = len(nodes)

    distances = np.full((n, n), np.inf)
    np.fill_diagonal(distances, 0)

    # Fill in finite shortest-path distances
    lengths = dict(nx.all_pairs_dijkstra_path_length(G, weight="distance"))
    node_to_i = {node: i for i, node in enumerate(nodes)}

    for u, targets in lengths.items():
        for v, d in targets.items():
            distances[node_to_i[u], node_to_i[v]] = d

    max_distance = np.max(distances[np.isfinite(distances)])
    for i, u in enumerate(nodes):
        for j, v in enumerate(nodes):
            if np.isinf(distances[i, j]):
                distances[i, j] = 1.2 * max_distance * (abs(u - v) / n)

    mds = MDS(
        n_components=2,
        metric="precomputed",
        init="classical_mds",
        random_state=42
    )

    pos_array = mds.fit_transform(D)
    return {nodes[i]: pos_array[i] for i in range(n)}