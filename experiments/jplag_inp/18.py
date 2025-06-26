
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    scaled_distance = np.exp(-distance_matrix / (max_distance + np.finfo(float).eps))
    normalized_distances = np.maximum(total_distance + np.finfo(float).eps, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 1.5 * normalized_distances), 0) * scaled_distance
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
