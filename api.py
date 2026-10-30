from dataclasses import dataclass
import os
import tempfile

import numpy as np

from callers.CATAD import CATADParameters, call_catad
from callers.MSTD import MSTDParameters, call_mstd
from data_manager import DataManager
from gzip import compress
from fastapi import Response
from pydantic import BaseModel, Field


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
        dataset = data_manager.get_dataset(identifier)
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
    def get_dataset_section(identifier: str, level: int, start_x: int, end_x: int, start_y: int, end_y: int, balanced: bool, test=False):
        dataset = data_manager.get_dataset(identifier)
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

    class TADCallRequest(BaseModel):
        callers: dict[str, MSTDParameters | CATADParameters]

    class TADList(BaseModel):
        caller: str
        start: int
        tads: list[tuple[int, int]]

    class TADCallResponse(BaseModel):
        tadlists: list[TADList]

    caller_registry: dict[str, dict[str, BaseModel | str]] = {
        "CATAD": {
            "balanced": False,  # doesn't work with balanced matrix
            "nan_filler": 0,  # assumes no nans, TODO read the paper
            "model": CATADParameters,
            "caller_function": call_catad
        },
        "MSTD": {
            "balanced": True,  # according to paper
            "nan_filler": None,  # fills nans
            "model": MSTDParameters,
            "caller_function": call_mstd
        }
    }

    def validate_parameters(request: TADCallRequest):
        result = {}

        for name, raw_parameters in request.callers.items():
            model = caller_registry[name]["model"]
            result[name] = model.model_validate(raw_parameters)

        return result

    # pull caller parameters from the request body
    @app.post("/tads/{identifier}/level/{level}/xregion/{start_x}/{end_x}/yregion/{start_y}/{end_y}")
    def detect_tads_in_region(identifier: str, level: int, start_x: int, end_x: int, start_y: int, end_y: int, caller_parameters: TADCallRequest, test=False) -> TADCallResponse:
        assert start_x == start_y and end_x == end_y  # matrix should be symmetrical

        dataset = data_manager.get_dataset(identifier)
        info = get_dataset_info(identifier)
        c = dataset.open_cooler(level)

        # create a temporary directory where TAD callers can work with files
        with tempfile.TemporaryDirectory() as tmpdirname:
            output_path = os.path.join(tmpdirname, "tads_out.txt")
                        
            validated_parameters = validate_parameters(caller_parameters)

            tadlists: list[TADList] = []
            for name, config in caller_registry.items():
                if name in validated_parameters:
                    # call tads and save results
                    # TODO test this extent filtering
                    extents = [c.extent(chromosome) for chromosome in info["chromosomes"]]
                    extents_filtered = [(start, end) for start, end in extents if end > start_x and start < end_x]
                    for start, end in extents_filtered:  # detect in all chromosomes that are included in range
                        caller_function = config["caller_function"]
                        matrix_name = f"matrix_{start}_{end}_{config["balanced"]}_{config["nan_filler"]}.txt"
                        matrix_path = os.path.join(tmpdirname, matrix_name)

                        # create the appropriate matrix if it hasn't been created yet
                        if not os.path.isfile(matrix_path):
                            matrix = dataset.get_region_pos(level, start, end, start, end, balanced=config["balanced"], nan_filler=config["nan_filler"])
                            np.savetxt(matrix_path, matrix, delimiter="\t", fmt="%g")

                        tad_list = caller_function(matrix_path, output_path, validated_parameters[name])
                        # the tads are in local chromosome coordinates
                        tadlists.append(TADList(caller=name, start=start, tads=tad_list))

        return TADCallResponse(tadlists=tadlists)
