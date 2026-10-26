from pydantic import BaseModel


class GraphNode(BaseModel):
    id: int
    x: float
    y: float


class GraphEdge(BaseModel):
    source: int
    target: int
    orig_dist: float


class GraphInput(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class MetricRequest(BaseModel):
    metric: str
    graph: GraphInput


class MetricResponse(BaseModel):
    metric: str
    score: float
