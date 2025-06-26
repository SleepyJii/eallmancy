import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    avg_distance = total_distance / (degree + 1)  # Average distance considering degree
    with np.errstate(divide='ignore', invalid='ignore'):
        relative_inverse_distance = np.where(distance_matrix > 0, 1 / (distance_matrix + avg_distance), 0)
    heuristic_matrix = relative_inverse_distance * degree
    return heuristic_matrix
