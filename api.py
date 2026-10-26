from pathlib import Path
from uuid import uuid4

from data_manager import DataManager
from data_store import ReconstructionDataStore
from settings import Settings
from gzip import compress
from fastapi import Response, Depends, HTTPException, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from graph_layouting import compute_graph_layout
from pastis_reconstruction import reconstruct_3d

import math
from metrics.registry import get_metric, available_metrics
from metrics.schemas import MetricRequest, MetricResponse
from metrics.graph_utils import build_graph, reconstruct_nx_graph

def create_api(app, settings: Settings, data_manager: DataManager, storage_manager: ReconstructionDataStore):
    security = HTTPBearer(auto_error=False)

    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if credentials is None:
            return None
        return data_manager.get_group_from_pw(credentials.credentials)
    
    # The gate screen in the frontend asks this before letting the user in, so it can tell a
    # wrong passcode apart from a server that is simply down. 401 means no passcode was sent,
    # 403 that one was sent but matches no group; anonymous callers use the other endpoints
    # without ever hitting this one, so both are errors here rather than "public access".
    @app.get("/auth")
    def check_passcode(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if credentials is None:
            raise HTTPException(status_code=401, detail="No passcode provided.")
        group = data_manager.get_group_from_pw(credentials.credentials)
        if group is None:
            raise HTTPException(status_code=403, detail="Unrecognised passcode.")
        return {"group": group}

    @app.get("/datasets")
    def fetch_datasets(group=Depends(authenticate)):
        return data_manager.get_dataset_ids(group)

    @app.get("/")
    def help():
        return "TODO"

    @app.get("/info/{identifier}")
    def get_dataset_info(identifier: str, group=Depends(authenticate)):
        return data_manager.get_dataset_info(identifier, group)

    @app.post("/upload")
    async def upload_dataset(file: UploadFile = File(...), group=Depends(authenticate)):
        if not settings.allow_uploads:
            raise HTTPException(status_code=403, detail="Uploads are disabled on this server.")

        name = Path((file.filename or "").replace("\\", "/")).name.replace("\x00", "").strip()
        stem, suffix = Path(name).stem, Path(name).suffix.lower()
        if not stem or suffix not in (".cool", ".mcool"):
            raise HTTPException(status_code=400, detail="Only .cool and .mcool files can be uploaded.")

        staging = Path(f"{data_manager.data_dir}/.upload-{uuid4().hex}.part")
        written = 0
        try:
            with staging.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    written += len(chunk)
                    out.write(chunk)
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        target = data_manager.free_upload_path(stem, suffix)
        staging.replace(target)
        dataset = data_manager.register(target, group)

        return {"identifier": dataset.get_identifier(), "info": dataset.get_info()}

    # Fetch tile data from a given dataset at selected level and tile coordinates
    # Importantly level zero == lowest detail (smallest total size)
    @app.get("/data/{identifier}/level/{level}/tile/{tile_x}/{tile_y}/balanced/{balanced}")
    def get_dataset_tile(identifier: str, level: int, tile_x: int, tile_y: int, balanced: bool, test=False, group=Depends(authenticate)):        
        dataset = data_manager.get_dataset(identifier, group)
        tile = dataset.get_tile(level, tile_x, tile_y, balanced)
        print(tile)
        if test:
            return {"matrix": tile.tolist()}
        compressed = compress(tile.tobytes())
        return Response(
            content=compressed,
            media_type="application/octet-stream",
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            }
        )
    
    @app.get("/data/{identifier}/level/{level}/xregion/{start_x}/{end_x}/yregion/{start_y}/{end_y}/balanced/{balanced}")
    def get_dataset_section(identifier: str, level: int, start_x: int, end_x: int, start_y: int, end_y: int, balanced: bool, test=False, group=Depends(authenticate)):
        dataset = data_manager.get_dataset(identifier, group)
        tile = dataset.get_region_pos(level, start_x, end_x, start_y, end_y, balanced)
        print(tile)
        if test:
            return {"matrix": tile.tolist()}
        compressed = compress(tile.tobytes())
        return Response(
            content=compressed,
            media_type="application/octet-stream",
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            }
        )
    
    @app.get("/chromosomes/{identifier}")
    def fetch_chromosome_annotations(identifier: str, level: int = 0, round: bool = False, group=Depends(authenticate)):
        dataset = data_manager.get_dataset(identifier, group)

        chrom_sizes = dataset.get_chromosome_annotations(level, round);
        res = dataset.resolutions[level]
        result = []
        total = 0

        for i, (name, size) in enumerate(chrom_sizes):
            start = total if i == 0 else total + res
            end = total + size
            result.append((name, start, end))
            total = end
        return result

    @app.get("/graph/{identifier}/level/{level}/type/{type}/position/{start}/{end}/balanced/{balanced}")
    def calculate_graph_layout(identifier: str, level: int, type: str, start: int, end: int, balanced: bool, infer_distances: bool=True, freq_filter: float=0, dist_filter: float = -1, close_weight: int = 3, group=Depends(authenticate)):
        dataset = data_manager.get_dataset(identifier, group)
        if settings.use_storage and storage_manager.graph_exists(identifier, level, type, start, end, balanced, infer_distances, freq_filter, dist_filter, close_weight):
            return storage_manager.load_graph(identifier, level, type, start, end, balanced, infer_distances, freq_filter, dist_filter, close_weight)

        matrix = dataset.get_region_pos(level, start, end, start, end, balanced)
        positions, _ = compute_graph_layout(matrix, type, infer_distances=infer_distances, freq_filter=freq_filter, dist_filter=(None if dist_filter <= 0 else dist_filter), mod_weight=close_weight)
        result = [[key, pos[0], pos[1]] for key, pos in positions.items()]
        if (settings.use_storage):
            storage_manager.store_graph(result, identifier, level, type, start, end, balanced, infer_distances, freq_filter, dist_filter, close_weight)
        return result

    @app.get("/reconstruct/{identifier}/level/{level}/type/{type}/position/{start}/{end}/balanced/{balanced}")
    def calculate_reconstruction(identifier: str, level: int, type: str, start: int, end: int, balanced: bool, group=Depends(authenticate)):
        dataset = data_manager.get_dataset(identifier, group)
        if settings.use_storage and storage_manager.reconstruction_exists(identifier, level, type, start, end, balanced):
            return storage_manager.load_reconstruction(identifier, level, type, start, end, balanced)

        matrix = dataset.get_region_pos(level, start, end, start, end, balanced)
        reconstruction = reconstruct_3d(matrix, type)
        if (settings.use_storage):
            storage_manager.store_reconstruction(reconstruction, identifier, level, type, start, end, balanced)
        return reconstruction

    # Returns a list of all available metrics, which can be used to evaluate a graph
    @app.get("/metrics")
    def list_metrics():
        return {"metrics": available_metrics()}

    # Evaluates the 2D Visualization graph of a dataset by a given metric and returns the score
    @app.get("/metrics/evaluate/{metric}/{identifier}/level/{level}/type/{type}/position/{start}/{end}/balanced/{balanced}")
    def evaluate_dataset_graph(metric: str, identifier: str, level: int, type: str, start: int, end: int, balanced: bool, infer_distances: bool=True, freq_filter: float=0, dist_filter: float = -1, close_weight: int = 3, group=Depends(authenticate)):
        layouted_data, orig_distances = calculate_graph_layout(identifier, level, type, start, end, balanced, infer_distances=infer_distances, freq_filter=freq_filter, dist_filter=dist_filter, close_weight=close_weight)
        try:
            _metric = get_metric(metric)
            graph = reconstruct_nx_graph(layouted_data, orig_distances)
            score = _metric.evaluate(graph)

            if not math.isfinite(score):
                raise ValueError("Metric returned a non-finite score.")

            return MetricResponse(
                metric=_metric.name,
                score=score,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    # Evaluates a custom graph by a given metric and returns the score
    @app.post("/metrics/evaluate", response_model=MetricResponse)
    def evaluate_custom_graph(request: MetricRequest):
        try:
            metric = get_metric(request.metric)
            graph = build_graph(request.graph)
            score = metric.evaluate(graph)

            if not math.isfinite(score):
                raise ValueError("Metric returned a non-finite score.")

            return MetricResponse(
                metric=metric.name,
                score=score,
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

