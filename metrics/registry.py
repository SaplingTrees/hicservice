from .base import IMetric
from .test_metric import EdgeCountMetric, OrigDistSumMetric
from .crossing_edges_metric import CrossingEdgesMetric
from .stress_metric import StressMetric


METRICS: dict[str, type[IMetric]] = {
    EdgeCountMetric().name: EdgeCountMetric,
    OrigDistSumMetric().name: OrigDistSumMetric,
    CrossingEdgesMetric().name: CrossingEdgesMetric,
    StressMetric().name: StressMetric,
}


def get_metric(name: str) -> IMetric:
    metric_class = METRICS.get(name)

    if metric_class is None:
        raise ValueError(f"Unknown metric: {name}")

    return metric_class()


def available_metrics() -> list[str]:
    return list(METRICS.keys())
