
import requests
import json
import os


def compare(a_id: int, a_code: str, b_id: int, b_code: str, min_token_match=7):
    return compare_many(min_token_match=min_token_match, **{a_id: a_code, b_id: b_code})

def compare_many(min_token_match=7, **solns):
    resp = requests.post(
        f"http://localhost:{os.environ.get('JPLAG_API_PORT', 9995)}/compare",
        json={'language':'python3', 'submissions':solns, 'minTokenMatch': min_token_match},
        timeout=30, retries=3
    )
    
    return json.loads(resp.content.decode('utf-8'))

def _jplag_token_intersection(a_code, b_code):
    rr = compare_many(
        a=a_code,
        b=b_code
    )
    if len(rr) == 0:
        return None
    rrr = rr[0]
    a_tokens = rrr['firstSubmission']['numberOfTokens']
    b_tokens = rrr['secondSubmission']['numberOfTokens']
    m_tokens = rrr['numberOfMatchedTokens']
    return a_tokens, b_tokens, m_tokens

def jplag_dists(a_code, b_code):
    a_tokens, b_tokens, m_tokens = _jplag_token_intersection(a_code, b_code)
    avg_dist = round(((m_tokens/a_tokens) + (m_tokens/b_tokens))/2.0, 3)
    max_dist = round(max((m_tokens/a_tokens), (m_tokens/b_tokens)), 3)
    return {'avg': avg_dist, 'max': max_dist}

def avg_jplag_dist(a_code, b_code):
    a_tokens, b_tokens, m_tokens = _jplag_token_intersection(a_code, b_code)
    return round(((m_tokens/a_tokens) + (m_tokens/b_tokens))/2.0, 3)
    
def max_jplag_dist(a_code, b_code):
    a_tokens, b_tokens, m_tokens = _jplag_token_intersection(a_code, b_code)
    return round(max((m_tokens/a_tokens), (m_tokens/b_tokens)), 3)
