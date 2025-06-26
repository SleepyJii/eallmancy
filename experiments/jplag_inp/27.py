import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    average_distance = total_distance / degree
    distance_penalty = np.where(distance_matrix > 0, distance_matrix / average_distance, 0)
    heuristic_matrix = np.exp(-distance_penalty) / degree
    return heuristic_matrix
