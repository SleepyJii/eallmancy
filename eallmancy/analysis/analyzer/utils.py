
import requests
import backoff
import numpy as np
from collections import defaultdict
import itertools
from itertools import chain, count
import os
import re
from typing import Dict, List

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
def get_codet5p_embeddings(
    prompts,
    base_url: str = "http://127.0.0.1:5050",
    model: str = "Salesforce/codet5p-110m-embedding",
    timeout: float = 30.0,
    cached_embeddings=None,
    encoding_format: str = "float",  # or "base64" (if you set that on your server)
) -> np.ndarray:
    """
    Call the local FastAPI embeddings shim and return a list of numpy arrays.
    """
    if cached_embeddings is None:
        cached_embeddings = {}

    url = f"{base_url.rstrip('/')}/v1/embeddings"
    headers = {}  # no auth by default

    cached_prmpt_idxs = [i for i, x in enumerate(prompts) if x in cached_embeddings]
    empty_prmpt_idxs  = [i for i, x in enumerate(prompts) if len(x) == 0 and x not in cached_embeddings]
    nonempty_prmpt_idxs = [i for i, x in enumerate(prompts) if len(x) != 0 and x not in cached_embeddings]
    nonempty_prmpts = [x for i, x in enumerate(prompts) if i in nonempty_prmpt_idxs]

    clean_data = {}
    if len(nonempty_prmpts) != 0:
        payload = {
            "model": model,
            "input": nonempty_prmpts,
            "encoding_format": encoding_format,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        if encoding_format.lower() == "base64":
            import base64
            for idx, rr in zip(nonempty_prmpt_idxs, data["data"]):
                vec = np.frombuffer(base64.b64decode(rr["embedding"]), dtype=np.float32)
                clean_data[idx] = vec
        else:
            # float list
            for idx, rr in zip(nonempty_prmpt_idxs, data["data"]):
                clean_data[idx] = np.array(rr["embedding"], dtype=np.float32)

    # assemble outputs preserving order; keep your "empty -> zero-length" convention
    res = [np.zeros((0,), dtype=np.float32) for _ in range(len(prompts))]
    for idx, rres in clean_data.items():
        res[idx] = rres
        cached_embeddings[prompts[idx]] = rres
    for idx in cached_prmpt_idxs:
        res[idx] = cached_embeddings[prompts[idx]]
    # any brand-new empty prompts remain zero-length; cache if you want:
    for idx in empty_prmpt_idxs:
        cached_embeddings[prompts[idx]] = res[idx]

    return res


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3,)
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
    


def cosine_sim(a, b):
    return (a / np.linalg.norm(a)).dot(b / np.linalg.norm(b))


