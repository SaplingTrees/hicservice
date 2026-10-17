import networkx as nx

from .schemas import GraphInput


def build_graph(data: GraphInput) -> nx.Graph:
    graph = nx.Graph()

    for node in data.nodes:
        graph.add_node(
            node.id,
            pos=(node.x, node.y),
        )

    for edge in data.edges:
        if not graph.has_node(edge.source):
            raise ValueError(
                f"Unknown edge source: {edge.source}"
            )

        if not graph.has_node(edge.target):
            raise ValueError(
                f"Unknown edge target: {edge.target}"
            )

        graph.add_edge(edge.source, edge.target)

    return graph

def reconstruct_nx_graph(layouted_data) -> nx.Graph:
    graph = nx.Graph()

    for idx, elem in enumerate(layouted_data):
        key = elem[0]
        posX = elem[1]
        posY = elem[2]

        graph.add_node(
            key,
            pos=(posX, posY),
        )

        if (idx > 0 and layouted_data[idx - 1][0] == key - 1):
            graph.add_edge(layouted_data[idx - 1][0], key)
    
    return graph
