import numpy as np

def heuristic(distance_matrix: np.ndarray) -> np.ndarray:
    # Calculate local density based on the degree of each node
    degree = np.count_nonzero(distance_matrix, axis=1, keepdims=True)
    
    # Calculate the total and maximum distances for normalization
    total_distance = np.sum(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    max_distance = np.max(distance_matrix, axis=1, keepdims=True) + np.finfo(float).eps
    
    # Compute a local density score inversely related to distances
    density_score = np.where(distance_matrix > 0, degree / distance_matrix, 0)
    
    # Normalize the density score by total distances
    normalized_density = density_score / total_distance
    
    # Incorporate a penalty for longer distances
    distance_penalty = np.exp(-1 * distance_matrix / max_distance)
    
    # Combine normalized density and distance penalty for final heuristic
    heuristic_matrix = normalized_density * distance_penalty

    return heuristic_matrix
