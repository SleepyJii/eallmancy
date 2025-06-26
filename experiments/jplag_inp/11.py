import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    # Calculate the degree of each vertex.
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)  
    # Calculate the total distance and add a small constant for numerical stability.
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps  
    # Calculate a smoothing factor based on the mean distance to mitigate the influence of outliers.
    mean_distance = np.mean(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps  
    # Use the reciprocal of the distance squared modified by the mean distance.
    adaptive_weights = 1 / (distance_matrix ** 2 + mean_distance)  
    with np.errstate(divide='ignore', invalid='ignore'):
        # Introduce a new scaling mechanism based on normalized total distances.
        normalized_scaling = total_distance / np.max(total_distance, axis=0)  
        heuristic_matrix = adaptive_weights * degree * normalized_scaling  
    return heuristic_matrix  
