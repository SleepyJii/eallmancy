



# EVOLVE START

import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.maximum(np.sum(distance_matrix > 0, axis=1, keepdims=True), 1)
    max_distance = np.max(distance_matrix, axis=1, keepdims=True)
    normalized_distances = np.maximum(max_distance, 1)
    weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2 * normalized_distances), 0)
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix

# EVOLVE END





