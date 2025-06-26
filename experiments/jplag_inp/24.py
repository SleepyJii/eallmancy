import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    edge_centrality = total_distance / (degree + np.finfo(float).eps)  # Calculate edge centrality
    scaled_distance = np.exp(-distance_matrix / max_distance)
    normalized_distances = np.maximum(total_distance, 1)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_centrality = np.where(distance_matrix > 0, 1 / (distance_matrix ** 2 * normalized_distances), 0) * scaled_distance
        
    heuristic_matrix = weighted_centrality * edge_centrality
    return heuristic_matrix
