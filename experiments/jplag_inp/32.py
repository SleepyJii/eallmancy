import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    threshold = np.percentile(distance_matrix[distance_matrix > 0], 75, interpolation='nearest')
    
    proximity_weight = np.exp(-distance_matrix / threshold)
    normalized_distances = np.maximum(total_distance, 1)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse = np.where(distance_matrix > 0, np.log1p(threshold / distance_matrix) * proximity_weight, 0)
    
    heuristic_matrix = weighted_inverse * degree
    return heuristic_matrix
