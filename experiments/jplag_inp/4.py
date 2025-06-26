import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    average_distance = np.mean(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    adjusted_distance = np.sqrt(distance_matrix) + np.finfo(float).eps
    inverse_sqrt_distance = np.where(adjusted_distance > 0, 1 / adjusted_distance, 0)
    heuristic_matrix = inverse_sqrt_distance / average_distance * degree * np.exp(-distance_matrix / average_distance)
    return heuristic_matrix
