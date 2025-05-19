



# EVOLVE START

import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.sum(distance_matrix > 0, axis=1, keepdims=True)
    weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2), 0)
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix

# EVOLVE END





