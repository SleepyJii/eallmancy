
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.sum(distance_matrix > 0, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    scaled_distance = np.power(max_distance, 2) / (distance_matrix + np.finfo(float).eps)
    normalized_distances = np.maximum(total_distance, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, scaled_distance / (distance_matrix ** 2 * normalized_distances), 0)
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
