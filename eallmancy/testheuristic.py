



# EVOLVE START
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    min_distance = np.min(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    inverse_distance = np.where(distance_matrix > 0, 1 / distance_matrix, 0)
    heuristic_matrix = inverse_distance / total_distance * degree * np.exp(-distance_matrix / min_distance)
    return heuristic_matrix

# EVOLVE END





