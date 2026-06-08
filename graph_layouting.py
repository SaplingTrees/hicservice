import numpy as np
from math import cbrt
from typing import Optional

import networkx as nx;
from networkx.drawing.nx_pydot import graphviz_layout
from sklearn.manifold import MDS

def distance_function(frequency: float) -> float:
    return 1 / cbrt(frequency)

def frequency_filter(frequency: float, threshold: float) -> bool:
    return not np.isnan(frequency) and frequency > threshold

def distance_filter(distance: float, threshold: Optional[float]) -> bool:
    return threshold is None or distance > threshold

def compute_graph_layout(matrix: np.array, type: str, infer_distances=True, freq_filter=0, dist_filter=None, mod_distance=1, mod_weight=2):
    G = nx.Graph()
    measured_distances = {}
    kamada_distances = {}
    n = matrix.shape[0]

    for i in range(n):
        for j in range(i + 1, n):
            frequency = matrix[i, j]

            if not frequency_filter(frequency, freq_filter):
                continue
            distance = distance_function(frequency)
            
            if not distance_filter(distance, dist_filter):
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

    index = {node: i for i, node in enumerate(nodes)}

    D = np.full((n, n), np.inf)
    np.fill_diagonal(D, 0)
    for u, v, data in G.edges(data=True):
        i, j = index[u], index[v]
        D[i, j] = data.get("distance", 1.0)
        D[j, i] = D[i, j]
    mds = MDS(
        n_components=2,
        metric="precomputed",
        random_state=42,
        init="classical_mds"
    )

    pos_array = mds.fit_transform(D)
    return {nodes[i]: pos_array[i] for i in range(n)}