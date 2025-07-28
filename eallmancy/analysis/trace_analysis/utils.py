
import numpy as np

def cosine_sim(a, b):
    return (a / np.linalg.norm(a)).dot(b / np.linalg.norm(b))
