from metrics.schemas import DatasetGraphRequest, LayoutParameters, MetricResponse
from data_manager import DataManager
from settings import Settings
from graph_layouting import compute_graph_layout
from metrics.graph_utils import reconstruct_nx_graph
from metrics.registry import METRICS, get_metric
from .metric_evaluation import pretty_print_metric_response

class Experiment:
    def __init__(self, dataset_request: DatasetGraphRequest, layout_parameters: LayoutParameters):
        self.dataset_request = dataset_request
        self.layout_parameters = layout_parameters
        self.graph = self.__build_graph()

    def __build_graph(self):
        settings: Settings = Settings()
        data_manager = DataManager(settings)
        
        # Retrieve dataset
        dataset = data_manager.get_dataset(self.dataset_request.identifier)

        # Generate graph layout
        matrix = dataset.get_region_pos(
            self.dataset_request.level,
            self.dataset_request.start,
            self.dataset_request.end,
            self.dataset_request.start,
            self.dataset_request.end,
            self.dataset_request.balanced
        )

        layout = self.layout_parameters

        positions, orig_distances = compute_graph_layout(
            matrix,
            self.dataset_request.type,
            infer_distances=layout.infer_distances,
            freq_filter=layout.freq_filter,
            dist_filter=(
                None if layout.dist_filter <= 0
                else layout.dist_filter
            ),
            mod_weight=layout.close_weight
        )

        layouted_data = [
            [key, pos[0], pos[1]]
            for key, pos in positions.items()
        ]

        # Reconstruct graph
        return reconstruct_nx_graph(layouted_data, orig_distances)

    def run_metric(self, metric, **parameters) -> MetricResponse:
        score = metric.evaluate(self.graph, **parameters)
        return MetricResponse(
            metric=metric.name,
            score=score,
        )

TO_EVAL = [
    (get_metric("crossing_edges"), {}),
    (get_metric("rmse"), {}),
    (get_metric("stress"), {
        "normalize": False,
        "weighting": "uniform",
        "selection": "edges"
    }),
    (get_metric("stress"), {
        "normalize": False,
        "weighting": "inverse_distance_squared",
        "selection": "edges"
    }),
    (get_metric("stress"), {
        "normalize": True,
        "weighting": "uniform",
        "selection": "edges"
    }),
    (get_metric("stress"), {
        "normalize": True,
        "weighting": "inverse_distance_squared",
        "selection": "edges"
    }),
    (get_metric("pearson_cc"), {}),
    (get_metric("spearman_cc"), {}),
]

def run_experiment(dr, lr):
    exp = Experiment(dr, lr)

    print(f"Running experiment for dataset: {dr.identifier}, level: {dr.level}, start: {dr.start}, end: {dr.end}, balanced: {dr.balanced}, layout type: {dr.type}")
    print(f"Layout parameters: infer_distances: {lr.infer_distances}, freq_filter: {lr.freq_filter}, dist_filter: {lr.dist_filter}, close_weight: {lr.close_weight}")
    for metric, params in TO_EVAL:
            pretty_print_metric_response(exp.run_metric(metric, **params))

def run_experiment1():
    dataset_request = DatasetGraphRequest(
        identifier="Rosa",
        level=0,
        start=0,
        end=169,
        balanced=True,
        type="kamada"
    )

    layout_parameters = LayoutParameters(
        infer_distances=False,
        freq_filter=0,
        dist_filter=-1,
        close_weight=3.0
    )

    run_experiment(dataset_request, layout_parameters)

def run_experiment2():
    dataset_request = DatasetGraphRequest(
        identifier="Rosa",
        level=0,
        start=0,
        end=169,
        balanced=True,
        type="kamada"
    )

    layout_parameters = LayoutParameters(
        infer_distances=False,
        freq_filter=0,
        dist_filter=-1,
        close_weight=2.0
    )

    run_experiment(dataset_request, layout_parameters)

run_experiment1()
run_experiment2()
