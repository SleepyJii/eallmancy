
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True)
    max_distance = np.max(distance_matrix, axis=1, keepdims=True)
    scaled_distance = np.exp(-distance_matrix / (max_distance + np.finfo(float).eps))
    normalized_distances = total_distance + np.finfo(float).eps
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2 * normalized_distances), 0) * scaled_distance
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
