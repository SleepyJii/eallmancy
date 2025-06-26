import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    normalized_inverse_distance = np.where(distance_matrix > 0, (1 / distance_matrix), 0)
    
    attenuation_factor = np.exp(-distance_matrix / (total_distance + np.finfo(float).eps))
    heuristic_matrix = normalized_inverse_distance * attenuation_factor * degree
    heuristic_matrix /= np.sum(heuristic_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    return heuristic_matrix
