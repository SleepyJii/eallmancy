import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    # Compute a varying weight for distance contributions based on absolute distances
    min_distance = np.min(distance_matrix[distance_matrix > 0], axis=1, keepdims=True)
    relative_distance = distance_matrix / (min_distance + np.finfo(float).eps)
    weight = np.exp(-relative_distance)
    
    # Compute the effective contribution from each node
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    normalized_distances = np.maximum(total_distance, 1)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_inverse_square = np.where(distance_matrix > 0, weight / (distance_matrix ** 2 * normalized_distances), 0)
        
    heuristic_matrix = weighted_inverse_square * degree
    return heuristic_matrix
