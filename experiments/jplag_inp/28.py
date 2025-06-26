import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    log_scaled_distance = np.log1p(distance_matrix) / max_distance  # Log scaling applied
    proximity_penalty = np.maximum(1 - (distance_matrix / max_distance), 0)  # Penalty for distance
    normalized_distances = np.maximum(total_distance, 1)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2 * normalized_distances), 0) * log_scaled_distance * proximity_penalty
    
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
