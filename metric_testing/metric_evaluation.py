from .sample_graphs import SampleGraphs
from metrics.schemas import MetricRequest, MetricResponse
from metrics.graph_utils import build_graph
from metrics.registry import get_metric, available_metrics
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

graphs = [
    SampleGraphs.get_sample_graph_1(),
    SampleGraphs.get_sample_graph_2(),
]

for idx, g in enumerate(graphs):
    for m in available_metrics():
        print("Evaluating sample graph ", idx + 1, " with ", m, " metric:")
        response = evaluate_custom_graph(MetricRequest(
            metric=m,
            graph=g
        ))
        pretty_print_metric_response(response)
