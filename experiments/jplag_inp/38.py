
import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps * degree
<<<<<<<< SEARCH
    scaled_distance = np.exp(-distance_matrix / max_distance)
========
    scaled_distance = np.log1p(-distance_matrix / max_distance) + 1  # Changed to log1p for smoother scaling
<<<<<<<< SEARCH
    normalized_distances = np.maximum(total_distance, 1)
========
    normalized_distances = np.maximum(total_distance, 1) + np.count_nonzero(distance_matrix, axis=1, keepdims=True)  # Added degree to normalization
<<<<<<<< SEARCH
    heuristic_matrix = weighted_inverse_square * degree
========
    heuristic_matrix = weighted_inverse_square * (degree + 1)  # Improved scaling with degree adjustment
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    scaled_distance = np.exp(-distance_matrix / max_distance)
    normalized_distances = np.maximum(total_distance, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2 * normalized_distances), 0) * scaled_distance
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
