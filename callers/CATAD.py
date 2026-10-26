import csv
import os
import subprocess
import sys

from pydantic import BaseModel, Field


class CATADParameters(BaseModel):
    """
    Args:
      CS_threshold (float): The threshold for cosion similarity.
    """
    CS_threshold: float = Field(default=0.8, ge=0.1, le=0.9)


def call_catad(matrix_path, output_path, parameters: CATADParameters):
    external_callers_path = "callers_external"

    # run the caller
    completed = subprocess.run(
        [
            sys.executable,
            os.path.join(
                external_callers_path, "CATAD", "CATAD.py"
            ),
            matrix_path,
            str(parameters.CS_threshold),
            output_path,
        ],
        check=True,
    )

    # get results
    catad_list = []
    with open(output_path, newline="") as file:
        reader = csv.reader(file, delimiter="\t")
        for start, end in reader:
            catad_list.append((start, end))

    return catad_list
