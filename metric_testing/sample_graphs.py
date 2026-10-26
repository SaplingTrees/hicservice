from metrics.schemas import GraphInput

class SampleGraphs:
    @staticmethod
    def get_sample_graph_1() -> GraphInput:
        nodes = [
            {"id": 1, "x": 0.0, "y": 0.0},
            {"id": 2, "x": 1.0, "y": 0.0},
            {"id": 3, "x": 1.0, "y": 1.0},
            {"id": 4, "x": 0.0, "y": 1.0},
        ]
        edges = [
            {"source": 1, "target": 2, "orig_dist": 1.0},
            {"source": 2, "target": 3, "orig_dist": 1.0},
            {"source": 3, "target": 4, "orig_dist": 1.0},
            {"source": 4, "target": 1, "orig_dist": 1.0},
        ]
        return GraphInput(nodes=nodes, edges=edges)

    @staticmethod
    def get_sample_graph_2() -> GraphInput:
        nodes = [
            {"id": 1, "x": 0.0, "y": 0.0},
            {"id": 2, "x": 1.0, "y": 0.0},
            {"id": 3, "x": 1.0, "y": 1.0},
        ]
        edges = [
            {"source": 1, "target": 2, "orig_dist": 1.0},
            {"source": 2, "target": 3, "orig_dist": 0.5},
        ]
        return GraphInput(nodes=nodes, edges=edges)
