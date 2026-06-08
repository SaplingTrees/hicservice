from data_manager import DataManager
from gzip import compress
from fastapi import Response
from graph_layouting import compute_graph_layout

def create_api(app, settings, data_manager: DataManager):
    @app.get("/datasets")
    def fetch_datasets():
        return data_manager.get_dataset_ids()

    @app.get("/")
    def read_root():
        return {"Hello": "World", "Datadir": settings.data_dir}

    @app.get("/info/{identifier}")
    def get_dataset_info(identifier: str):
        return data_manager.get_dataset_info(identifier)

    # Fetch tile data from a given dataset at selected level and tile coordinates
    # Importantly level zero == lowest detail (smallest total size)
    @app.get("/data/{identifier}/level/{level}/tile/{tile_x}/{tile_y}")
    def get_dataset_sile(identifier: str, level: int, tile_x: int, tile_y: int, test=False):
        dataset = data_manager.get_dataset(identifier)
        tile = dataset.get_tile(level, tile_x, tile_y)
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
    
    @app.get("/graph/{identifier}/level/{level}/type/{type}/position/{start}/{end}")
    def calculate_graph_layout(identifier: str, level: int, type: str, start: int, end: int):
        dataset = data_manager.get_dataset(identifier)
        matrix = dataset.get_region_pos(level, start, end, start, end)
        positions = compute_graph_layout(matrix, type, False)
        print(positions)
        result = [[key, pos[0], pos[1]] for key, pos in positions.items()]
        return result



