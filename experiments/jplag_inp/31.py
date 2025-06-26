import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    num_nodes = distance_matrix.shape[0]
    average_distance = np.mean(np.where(distance_matrix > 0, distance_matrix, np.inf), axis=1, keepdims=True)
    min_distance = np.min(np.where(distance_matrix > 0, distance_matrix, np.inf), axis=1, keepdims=True) + np.finfo(float).eps
    closeness_factor = (1 / average_distance) * np.exp(-min_distance)
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    
    # Enhanced scoring scheme based on closeness
    heuristic_matrix = closeness_factor * degree
    return heuristic_matrix
