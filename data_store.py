from pathlib import Path
from typing import List

class ReconstructionDataStore:
    store_dir = ""
    store_path: Path = Path()

    # datasets: dict[str, CoolFile] = dict()

    def __init__(self, settings):
        self.store_dir = settings.store_dir
        self.store_path = Path(self.store_dir)
        (self.store_path / "2d").mkdir(exist_ok=True)
        (self.store_path / "3d").mkdir(exist_ok=True)


    def _graph_path(self, identifier: str, level: int, type: str, start: int, end: int, balanced: bool, infer_distances: bool, freq_filter: float, dist_filter: float, close_weight: float) -> Path:
        filename = f"{identifier}-{level}-{type}-{start}-{end}-{int(balanced)}-{int(infer_distances)}-{freq_filter}-{dist_filter}-{close_weight}.txt"
        return self.store_path / "2d" / filename

    def graph_exists(self, identifier: str, level: int, type: str, start: int, end: int, balanced: bool, infer_distances: bool, freq_filter: float, dist_filter: float, close_weight: float) -> bool:
        return self._graph_path(identifier, level, type, start, end, balanced, infer_distances, freq_filter, dist_filter, close_weight).is_file()

    def store_graph(self, data: list[list[float]], identifier: str, level: int, type: str, start: int, end: int, balanced: bool, infer_distances: bool, freq_filter: float, dist_filter: float, close_weight: float):
        with open(self._graph_path(identifier, level, type, start, end, balanced, infer_distances, freq_filter, dist_filter, close_weight), "w") as f:
            for row in data:
                f.write(",".join(str(entry) for entry in row) + "\n")

    def load_graph(self, identifier: str, level: int, type: str, start: int, end: int, balanced: bool, infer_distances: bool, freq_filter: float, dist_filter: float, close_weight: float) -> list[list[float]]:
        with open(self._graph_path(identifier, level, type, start, end, balanced, infer_distances, freq_filter, dist_filter, close_weight), "r") as f:
            return [[float(entry) for entry in line.split(",")] for line in f if line.strip()]

    def _reconstruction_path(self, identifier: str, level: int, type: str, start: int, end: int, balanced: bool) -> Path:
        filename = f"{identifier}-{level}-{type}-{start}-{end}-{int(balanced)}.txt"
        return self.store_path / "3d" / filename

    def reconstruction_exists(self, identifier: str, level: int, type: str, start: int, end: int, balanced: bool) -> bool:
        return self._reconstruction_path(identifier, level, type, start, end, balanced).is_file()

    def store_reconstruction(self, data: list[list[float]], identifier: str, level: int, type: str, start: int, end: int, balanced: bool):
        with open(self._reconstruction_path(identifier, level, type, start, end, balanced), "w") as f:
            for row in data:
                f.write(",".join(str(entry) for entry in row) + "\n")

    def load_reconstruction(self, identifier: str, level: int, type: str, start: int, end: int, balanced: bool) -> list[list[float]]:
        with open(self._reconstruction_path(identifier, level, type, start, end, balanced), "r") as f:
            return [[float(entry) for entry in line.split(",")] for line in f if line.strip()]


