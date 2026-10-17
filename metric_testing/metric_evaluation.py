from .sample_graphs import SampleGraphs
from metrics.schemas import MetricRequest, MetricResponse
from metrics.graph_utils import build_graph
from metrics.registry import get_metric
import math

def evaluate_custom_graph(request: MetricRequest):
    metric = get_metric(request.metric)
    graph = build_graph(request.graph)
    score = metric.evaluate(graph)

    if not math.isfinite(score):
        raise ValueError("Metric returned a non-finite score.")

    return MetricResponse(
        metric=metric.name,
        score=score,
    )

def pretty_print_metric_response(response: MetricResponse):
    print(f"Metric: {response.metric}")
    print(f"Score: {response.score:.4f}")





print("Evaluating sample graph 1 with edge_count metric:")
response = evaluate_custom_graph(MetricRequest(
    metric="edge_count",
    graph=SampleGraphs.get_sample_graph_1()
))
pretty_print_metric_response(response)

print("Evaluating sample graph 2 with edge_count metric:")
response = evaluate_custom_graph(MetricRequest(
    metric="edge_count",
    graph=SampleGraphs.get_sample_graph_2()
))
pretty_print_metric_response(response)
