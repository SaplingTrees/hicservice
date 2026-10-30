import csv
from typing import Literal

from MSTDlib import MSTD_v1
from pydantic import BaseModel, Field


class MSTDParameters(BaseModel):
    MDHD: int = 7
    symmetry: Literal[0, 1] = 1
    window: int = Field(default=7, ge=5, le=10)

def call_mstd(matrix_path, output_path, parameters: MSTDParameters):
    tad_list = []

    # TODO figure out if we can redirect the output of this function
    MSTD_v1.MSTD(matrix_path, output_path, MDHD=parameters.MDHD, symmetry=parameters.symmetry, window=parameters.window, visualization=0)

    with open(output_path, newline="") as file:
        reader = csv.reader(file, delimiter="\t")
        next(reader, None)  # skip the header
        for start, end, center in reader:
            tad_list.append((start, end))

    return tad_list
