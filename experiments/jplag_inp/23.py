import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    min_distance = np.min(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    log_scaled_distance = np.log(total_distance) - np.log(distance_matrix + np.finfo(float).eps)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_log = np.where(distance_matrix > 0, log_scaled_distance, 0) / (distance_matrix + np.finfo(float).eps)
    
    heuristic_matrix = weighted_log * degree
    return heuristic_matrix
