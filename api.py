from data_manager import DataManager
from gzip import compress
from fastapi import Response
import math
import numpy as np
import time

def create_api(app, settings, data_manager: DataManager):
    @app.get("/datasets")
    def fetch_datasets():
        return data_manager.get_dataset_ids()

    @app.get("/")
    def help():
        return "TODO"

    @app.get("/info/{identifier}")
    def get_dataset_info(identifier: str):
        return data_manager.get_dataset_info(identifier)

    # Fetch tile data from a given dataset at selected level and tile coordinates
    # Importantly level zero == lowest detail (smallest total size)
    @app.get("/data/{identifier}/level/{level}/tile/{tile_x}/{tile_y}/balanced/{balanced}")
    def get_dataset_tile(identifier: str, level: int, tile_x: int, tile_y: int, balanced: bool, test=False):
        start = time.perf_counter()
        dataset = data_manager.get_dataset(identifier)
        tile = dataset.get_tile(level, tile_x, tile_y, balanced)
        tile = tile.astype(np.float32, copy=False)
        max_value = float(tile.max()) if tile.size else 0.0
        if not math.isfinite(max_value) or max_value < 0.0:
            max_value = 0.0
        if test:
            end = time.perf_counter() - start
            print(f"Execution time: {end:.6f}s")
            return {"matrix": tile.tolist(), "max_value": max_value}
        compressed = compress(tile.tobytes(), compresslevel=1)
        end = time.perf_counter() - start
        print(f"Execution time: {end:.6f}s")
        return Response(
            content=compressed,
            media_type="application/octet-stream",
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
                "X-Tile-Max-Value": f"{max_value:.9g}",
            }
        )
    
    @app.get("/data/{identifier}/level/{level}/xregion/{start_x}/{end_x}/yregion/{start_y}/{end_y}/balanced/{balanced}")
    def get_dataset_section(identifier: str, level: int, start_x: int, end_x: int, start_y: int, end_y: int, balanced: bool, test=False):
        dataset = data_manager.get_dataset(identifier)
        tile = dataset.get_region_pos(level, start_x, end_x, start_y, end_y, balanced)
        if test:
            return {"matrix": tile.tolist()}
        compressed = compress(tile.tobytes(), compresslevel=1)
        return Response(
            content=compressed,
            media_type="application/octet-stream",
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            }
        )
    
    @app.get("/chromosomes/{identifier}")
    def fetch_chromosome_annotations(identifier: str, level: int = 0, round: bool = False):
        dataset = data_manager.get_dataset(identifier)

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