from pydantic import BaseModel, Field
from typing import Any


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
    parameters: dict[str, Any] = Field(default_factory=dict)


class MetricResponse(BaseModel):
    metric: str
    score: float

class DatasetGraphRequest(BaseModel):
    identifier: str
    level: int
    type: str
    start: int
    end: int
    balanced: bool


class LayoutParameters(BaseModel):
    infer_distances: bool = True
    freq_filter: float = 0.0
    dist_filter: float = -1
    close_weight: int = 3


class DatasetMetricRequest(BaseModel):
    metric: str
    dataset: DatasetGraphRequest
    layout_parameters: LayoutParameters = LayoutParameters()
    metric_parameters: dict[str, Any] = Field(default_factory=dict)
