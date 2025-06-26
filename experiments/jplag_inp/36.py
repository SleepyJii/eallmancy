import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    min_distance = np.min(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    
    harmonic_mean = 2 / (1 / min_distance + 1 / (total_distance - min_distance))
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_harmonic = np.where(distance_matrix > 0, harmonic_mean / distance_matrix, 0)
    
    heuristic_matrix = weighted_harmonic * degree
    return heuristic_matrix
