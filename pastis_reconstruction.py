from pastis.optimization.mds import estimate_X as mds_estimate_X
from pastis.optimization.poisson_structure import estimate_X as poisson_estimate_X


import numpy as np

def reconstruct_3d(matrix: np.array, type: str) -> list[list[float]]:
    match type:
        case "mds":
            return mds_estimate_X(matrix, random_state=42).tolist()
        case "poisson":
            return poisson_estimate_X(matrix, random_state=42).tolist()
        case _:
            raise ValueError("Reconstruction type " + type + " not supported.")