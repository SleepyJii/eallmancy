import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    mean_distance = np.mean(np.where(distance_matrix > 0, distance_matrix, np.inf), axis=1, keepdims=True) + np.finfo(float).eps
    harmonic_mean = degree / np.sum(1 / (distance_matrix + (distance_matrix == 0) * np.inf), axis=1, keepdims=True)
    normalized_distance = total_distance / mean_distance
    heuristic_matrix = harmonic_mean * (1 / normalized_distance) * degree
    return heuristic_matrix
