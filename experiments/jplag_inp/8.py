import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    inverse_distance = np.where(distance_matrix > 0, 1 / distance_matrix, 0)
    summed_inverse_distance = np.sum(inverse_distance, axis=1, keepdims=True) + np.finfo(float).eps
    log_summed_inverse = np.log(summed_inverse_distance)
    softmax_weights = np.exp(log_summed_inverse - np.max(log_summed_inverse, axis=0))
    heuristic_matrix = softmax_weights * degree
    return heuristic_matrix
