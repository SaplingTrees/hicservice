from pathlib import Path

from data_manager import DataManager
from data_store import ReconstructionDataStore
from settings import Settings
from gzip import compress
from fastapi import Response, Depends, HTTPException, Request, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from graph_layouting import compute_graph_layout
from pastis_reconstruction import reconstruct_3d
from upload_security import (
    assert_stored_outside_webroot,
    check_declared_size,
    check_upload_request,
    discard_stale_uploads,
    safe_upload_name,
    staging_path,
    store_upload,
)

def create_api(app, settings: Settings, data_manager: DataManager, storage_manager: ReconstructionDataStore):
    assert_stored_outside_webroot(app, [settings.data_dir, settings.temp_data_dir])
    discard_stale_uploads([settings.data_dir, settings.temp_data_dir])

    security = HTTPBearer(auto_error=False)

    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if credentials is None:
            return None
        return data_manager.get_group_from_pw(credentials.credentials)
    
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
    async def upload_dataset(
        request: Request,
        file: UploadFile = File(...),
        temporary: bool = True,
        group=Depends(authenticate),
    ):
        if not settings.allow_uploads:
            raise HTTPException(status_code=403, detail="Uploads are disabled on this server.")

        check_upload_request(request, settings.allowed_origin_patterns)

        # Sanitised and length-checked before the extension is read, so the extension that gets
        # approved is the one belonging to the name that will actually be stored.
        stem, suffix = safe_upload_name(file.filename, settings.max_filename_length)
        max_bytes = settings.max_upload_mb * 1024 * 1024
        check_declared_size(request.headers.get("content-length"), max_bytes)

        staging_dir = settings.temp_data_dir if temporary else settings.data_dir
        Path(staging_dir).mkdir(parents=True, exist_ok=True)
        staging = staging_path(staging_dir)
        try:
            await store_upload(file, staging, max_bytes)
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        try:
            target = data_manager.find_free_filename(stem, suffix, temporary)
            staging.replace(target)
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
        dataset, passkey = data_manager.register(target, group, temporary)

        return {
            "identifier": dataset.get_identifier(),
            "info": dataset.get_info(),
            "passkey": passkey,
        }

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
        positions = compute_graph_layout(matrix, type, infer_distances=infer_distances, freq_filter=freq_filter, dist_filter=(None if dist_filter <= 0 else dist_filter), mod_weight=close_weight)
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

