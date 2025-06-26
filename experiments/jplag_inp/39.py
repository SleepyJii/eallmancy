import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    min_distance = np.min(distance_matrix[distance_matrix > 0], axis=1, keepdims=True) + np.finfo(float).eps
    log_scaled_distance = np.log1p(distance_matrix) / min_distance
    reciprocal_mean = np.reciprocal(np.mean(distance_matrix + np.finfo(float).eps, axis=1, keepdims=True))
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse = np.where(distance_matrix > 0, reciprocal_mean * log_scaled_distance, 0)
    heuristic_matrix = weighted_inverse * degree
    return heuristic_matrix
