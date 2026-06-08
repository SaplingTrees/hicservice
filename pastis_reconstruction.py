from pastis.optimization.mds import estimate_X as mds_estimate_X
from pastis.optimization.poisson_structure import estimate_X as poisson_estimate_X


import numpy as np

def reconstruct_3d(matrix: np.array, type: str) -> np.ndarray:
    match type:
        case "mds":
            return mds_estimate_X(matrix).tolist()
        case "poisson":
            return poisson_estimate_X(matrix).tolist()
        case _:
            raise ValueError("Reconstruction type " + type + " not supported.")