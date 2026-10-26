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
        tads: list[tuple[int, int]]

    class TADCallResponse(BaseModel):
        tadlists: list[TADList]

    caller_registry: dict[str, dict[str, BaseModel | str]] = {
        "CATAD": {
            "model": CATADParameters,
            "call_caller": call_catad
        },
        "MSTD": {
            "model": MSTDParameters,
            "call_caller": call_mstd
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

        # CATAD doesn't expect balanced matrix
        matrix = dataset.get_region_pos(level, start_x, end_x, start_y, end_y, balanced=False)
        # MSTD expects balanced matrix
        matrix_balanced = dataset.get_region_pos(level, start_x, end_x, start_y, end_y, balanced=True)

        # create a temporary directory where TAD callers can work with files
        with tempfile.TemporaryDirectory() as tmpdirname:
            matrix_path = os.path.join(tmpdirname, "matrix.txt")
            matrix_balanced_path = os.path.join(tmpdirname, "matrix_balanced.txt")
            output_path = os.path.join(tmpdirname, "tads_out.txt")

            # save both balanced and unbalanced version since different callers have different assumptions
            np.savetxt(matrix_path, matrix, delimiter="\t", fmt="%g")
            np.savetxt(matrix_balanced_path, matrix_balanced, delimiter="\t", fmt="%g")
            
            validated_parameters = validate_parameters(caller_parameters)

            result: list[TADList] = []
            for name, data in caller_registry.items():
                if name in validated_parameters:
                    tad_list = data["call_caller"](matrix_path, output_path, validated_parameters[name])
                    result.append(TADList(caller=name, tads=tad_list))

        return TADCallResponse(tadlists=result)
