import requests
from eallmancy.analysis.utils import ancestor_mapdists, latest_common_ancestor, heritage_distance, heritage_distances
import jplag
from jplag import calc_jplag_distances
import numpy as np


from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MatchSegment:
    st_line: int
    en_line: int
    confidence: float

@dataclass
class HeritableIdea:
    matching_segments: Dict[int, MatchSegment]
    llm_description: str
    fitness_quantiles: List[float]

@dataclass
class EngineTraceAnalysis:
    jplag_distances: np.ndarray
    embed_distances: np.ndarray
    herit_distances: np.ndarray
    salient_ideas: List[HeritableIdea]




def get_code_embedding(
    prompt: str,
    host: str = 'localhost',
    model: str = 'manutic/nomic-embed-code',
    port: int = 5050,
    timeout: float = 30.0
) -> list[float]:
    url = f"http://{host}:{port}/api/embeddings"
    payload = {
        "model": model,
        "prompt": prompt
    }

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    return np.array(data.get("embedding", []))

def get_code_embeddings(
    prompts: List[str],
    *args,
    **kwargs
) -> list[float]:
    return [get_code_embedding(p, *args, **kwargs) for p in prompts]

def cosine_sim(a, b):
    return (a / np.linalg.norm(a)).dot(b / np.linalg.norm(b))

# res = get_code_embeddings(["def testme(a,b):\n\treturn a+b", "def testme(a,b):\n\treturn b+a"], timeout=600)
# print(cosine_sim(*res))


def _scrape_ideas(ttrace, jplag_dist, embed_dist, herit_dist):
    # TODO: implement
    return []

def build_analysis(ttrace):
    # JPLAG
    (_, _, jplag_dict), _, _ = calc_jplag_distances(ttrace, verbose=True)
    jplag_distances = np.zeros((len(ttrace.list),len(ttrace.list)))
    jplag_distances = jplag_matrix
    for (a,b), dd in jplag_dict.items():
        d = dd['avg']
        if math.isinf(d):
            continue
        jplag_distances[a,b] = d
        jplag_distances[b,a] = d

    # CODE EMBED
    embed_distances = np.zeros((len(ttrace.list),len(ttrace.list)))
    soln_vects = dict()
    def cached_solnvect(nn):
        if nn not in soln_vects.keys():
            soln_vects[nn] = get_code_embedding(ttrace.list[nn].program)
        return soln_vects[nn]
    
    for na, arta in enumerate(ttrace.list):
        for nb, artb in enumerate(ttrace.list):
            ddd = cosine_sim(cached_solnvect(na), cached_solnvect(nb))
            embed_distances[na,nb] = ddd
            embed_distances[nb,na] = ddd
    del soln_vects

    # heritage distances
    heritages = heritage_distances(ttrace.graph)
    herit_distances = np.zeros((len(ttrace.list),len(ttrace.list))) * np.nan
    
    for (a,b), d in heritages.items():
        if math.isinf(d):
            continue
        herit_distances[a,b] = d

    salient_ideas = _scrape_ideas(ttrace, jplag_distances, embed_distances, herit_distances)
    return EngineTraceAnalysis(
        jplag_distances,
        embed_distances,
        herit_distances,
        salient_ideas
    )

# res = build_analysis(ttrace)







def find_centered_clusters(ttrace, res: EngineTraceAnalysis, k=2, allowed_eps=0.3, min_members=3):
    masked_jplag_matrix = res.jplag_distances.copy()
    
    # nan out everyone but close relatives
    masked_jplag_matrix[np.isnan(res.herit_distances) | (res.herit_distances > k)] = np.nan
    
    # nan out divergent neighbors
    masked_jplag_matrix[res.jplag_distances < (1-allowed_eps)] = np.nan
    
    centered_clusters = dict()
    for nn in range(len(ttrace.list)):
        vv = masked_jplag_matrix[nn,:]
        nonna_fits = [(i,x) for i, x in enumerate(vv) if not np.isnan(x)]
        # nonna_fits = []
        if len(nonna_fits) < min_members:
            continue
        centered_clusters[nn] = nonna_fits
    return centered_clusters


from itertools import count

_SEG_ID_GEN = count(1)  # starts at 1

def _get_id():
    return next(_SEG_ID_GEN)


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
                # if f_idx == 14 and 18>=m_dd['startOfFirst'] and 18<m_dd['startOfFirst']+m_dd['length']:
                #     print(f"\tst:{m_dd['startOfFirst']}->en:{m_dd['startOfFirst']+m_dd['length']}  matches {s_idx}T{m_dd['startOfSecond']}")
                subm_stats['matchcounts'][s_idx][m_dd['startOfSecond']:m_dd['startOfSecond']+m_dd['length']] += 1
                # if s_idx == 14 and 18>=m_dd['startOfSecond'] and 18<m_dd['startOfSecond']+m_dd['length']:
                #     print(f"\tst:{m_dd['startOfSecond']}->en:{m_dd['startOfSecond']+m_dd['length']}  matches {f_idx}T{m_dd['startOfFirst']}")
    except Exception as e:
        if not _jplag_api_was_alive and jplag.api_handler.is_alive:
            jplag.api_handler.cleanup()
        raise e
    if not _jplag_api_was_alive and jplag.api_handler.is_alive:
        jplag.api_handler.cleanup()
            
    return subm_stats









