from .base import IMetric
from .test_metric import EdgeCountMetric, OrigDistSumMetric
from .crossing_edges_metric import CrossingEdgesMetric
from .stress_metric import StressMetric
from .RMSE_metric import RMSEMetric
from .pearson_cc_metric import PearsonCorrelationCoefficientMetric
from .spearman_cc_metric import SpearmanCorrelationCoefficientMetric


METRICS: dict[str, type[IMetric]] = {
    EdgeCountMetric().name: EdgeCountMetric,
    OrigDistSumMetric().name: OrigDistSumMetric,
    CrossingEdgesMetric().name: CrossingEdgesMetric,
    StressMetric().name: StressMetric,
    RMSEMetric().name: RMSEMetric,
    PearsonCorrelationCoefficientMetric().name: PearsonCorrelationCoefficientMetric,
    SpearmanCorrelationCoefficientMetric().name: SpearmanCorrelationCoefficientMetric,
}


def get_metric(name: str) -> IMetric:
    metric_class = METRICS.get(name)

    if metric_class is None:
        raise ValueError(f"Unknown metric: {name}")

    return metric_class()


def available_metrics() -> list[str]:
    return list(METRICS.keys())
