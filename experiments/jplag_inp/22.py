
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    median_distance = np.median(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    scaled_distance = np.exp(-distance_matrix / median_distance)
    normalized_distances = np.where(total_distance > 1, total_distance, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2 * normalized_distances), 0) * scaled_distance * np.log1p(distance_matrix)
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
