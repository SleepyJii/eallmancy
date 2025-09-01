
import backoff
import requests
import json
import os
import numpy as np
import eallmancy.analysis.jplag as jplag


from itertools import count

_SEG_ID_GEN = count(1)  # starts at 1
def _get_id():
    return next(_SEG_ID_GEN)


def compare(a_id: int, a_code: str, b_id: int, b_code: str, min_token_match=7):
    return compare_many(min_token_match=min_token_match, **{a_id: a_code, b_id: b_code})

@backoff.on_exception(
    backoff.expo,
    requests.exceptions.RequestException,
    max_tries=3,
)
def compare_many(min_token_match=7, **solns):
    resp = requests.post(
        f"http://localhost:{os.environ.get('JPLAG_API_PORT', 9995)}/compare",
        json={'language':'python3', 'submissions':solns, 'minTokenMatch': min_token_match},
        timeout=30
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






def clean_compare_many(min_token_match=7, ignore_api_status=False, **kwargs):
    _jplag_api_was_alive = jplag.api_handler.is_alive

    try:
        if not _jplag_api_was_alive and not ignore_api_status:
            jplag.api_handler.start()
        rr = jplag.jplag_compare_many(min_token_match=min_token_match, **kwargs)
        
        subm_stats = {
            'submissions': dict(),
            'comparisons': dict(),
            'matchcounts': dict()
        }
        
        for ss in rr:
            f_subm = ss['firstSubmission']
            f_idx = int(f_subm['name'])
            s_subm = ss['secondSubmission']
            s_idx = int(s_subm['name'])
            subm_stats['submissions'][f_idx] = f_subm
            subm_stats['submissions'][s_idx] = s_subm
            for mm in ss['matches']:
                mm['id'] = _get_id()
            subm_stats['comparisons'][(min(f_idx, s_idx), max(f_idx, s_idx))] = {
                'matches': ss['matches'],
                'num_matches': ss['numberOfMatchedTokens'],
                'first_idx': f_idx,
                'second_idx': s_idx,
            }
        
        ## .... is anything below here even used in the end?
        for f_idx, f_dd in subm_stats['submissions'].items():
            subm_stats['matchcounts'][f_idx] = np.zeros((f_dd['numberOfTokens'],))
        
        for (a_idx, b_idx), c_dd in subm_stats['comparisons'].items():
            for m_dd in c_dd['matches']:
                f_idx, s_idx = c_dd['first_idx'], c_dd['second_idx']
                subm_stats['matchcounts'][f_idx][m_dd['startOfFirst']:m_dd['startOfFirst']+m_dd['length']] += 1
                subm_stats['matchcounts'][s_idx][m_dd['startOfSecond']:m_dd['startOfSecond']+m_dd['length']] += 1
    except Exception as e:
        if not _jplag_api_was_alive and jplag.api_handler.is_alive:
            jplag.api_handler.cleanup()
        raise e
    if not _jplag_api_was_alive and jplag.api_handler.is_alive:
        jplag.api_handler.cleanup()
            
    return subm_stats
