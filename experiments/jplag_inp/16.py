import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    min_distance = np.min(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    linear_scale = (total_distance - distance_matrix) / total_distance
    exp_decay = np.exp(-distance_matrix / min_distance)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse = np.where(distance_matrix > 0, linear_scale * exp_decay / distance_matrix, 0)
    
    heuristic_matrix = weighted_inverse * degree
    return heuristic_matrix
