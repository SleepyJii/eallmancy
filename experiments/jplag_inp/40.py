import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    log_distance = np.log(total_distance)
    inverse_distance = np.where(distance_matrix > 0, 1 / (distance_matrix + np.finfo(float).eps), 0)
    heuristic_matrix = inverse_distance * degree * (1 / log_distance)
    return heuristic_matrix
