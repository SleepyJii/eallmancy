
import os
import requests
import numpy as np
from collections import defaultdict
import itertools
from itertools import chain, count
import os
import re
from typing import Dict, List



def get_openai_embeddings(
    prompts,
    api_key: str = os.environ.get('OPENAI_API_KEY'),
    model: str = 'text-embedding-3-small',
    timeout: float = 30.0,
    cached_embeddings=dict()
) -> np.ndarray:
    """
    Call OpenAI's embedding endpoint and return the embedding as a numpy array.
    """
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    cached_prmpt_idxs = [i for i, x in enumerate(prompts) if x in cached_embeddings.keys()]
    empty_prmpt_idxs = [i for i, x in enumerate(prompts) if len(x)==0 and x not in cached_embeddings.keys()]
    nonempty_prmpt_idxs = [i for i, x in enumerate(prompts) if len(x)!=0 and x not in cached_embeddings.keys()]
    nonempty_prmpts = [x for i, x in enumerate(prompts) if i in nonempty_prmpt_idxs]

    if len(nonempty_prmpts) != 0:
        payload = {
            "model": model,
            "input": nonempty_prmpts
        }
    
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        
        # The response contains `data: [{"embedding": [...], ...}]`
        clean_data = {idx: np.array(rr['embedding']) for idx, rr in zip(nonempty_prmpt_idxs, data["data"])}
    else:
        clean_data = dict()

    
    res = [np.zeros((0,)) for _ in range(len(prompts))]
    for idx, rres in clean_data.items():
        res[idx] = rres
        cached_embeddings[prompts[idx]] = rres
    for idx in cached_prmpt_idxs:
        res[idx] = cached_embeddings[prompts[idx]]
    return res
    