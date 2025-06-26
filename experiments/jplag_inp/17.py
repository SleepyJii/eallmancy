
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    adjusted_distance = np.maximum(total_distance, 1)
    inverse_distance = np.where(distance_matrix > 0, 1 / distance_matrix, 0)
    scaled_distance = np.exp(-distance_matrix / adjusted_distance)
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse = np.where(distance_matrix > 0, inverse_distance / adjusted_distance, 0) * scaled_distance
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
