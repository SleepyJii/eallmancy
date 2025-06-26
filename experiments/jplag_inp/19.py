import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    small_value = np.finfo(float).eps
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + small_value
    min_distance = np.min(distance_matrix + small_value, axis=1, keepdims=True)  # Adding a minimal threshold
    inverse_distance = np.where(distance_matrix > 0, 1 / distance_matrix, 0)  # Simple inverse distance
    weighted_inverse = inverse_distance / (total_distance + small_value)  # Normalized by total distance
    heuristic_matrix = weighted_inverse * degree * (1 - (min_distance / total_distance))  # Adjusting by min distance
    return heuristic_matrix
