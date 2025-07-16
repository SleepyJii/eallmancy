
import requests
import numpy as np
from collections import defaultdict
from itertools import chain
import os
import re
from typing import Dict

from eallmancy.artifacts.artifact import Artifact
from eallmancy.engine.llm_solution_engine_v3 import EngineV3

from trace_analysis.greedy_salidea import *
from trace_analysis.atomization import *
from trace_analysis.segm_printing import *
from trace_analysis.idea_distillation import DistilledIdeaClusters, distill_atom_clusters





def distinct_subsegments(atom_list, persp_id, soln_filter=None, neg_filter=False):
    """
    Yields contiguous sequences of atoms where:
      - the solution memberships intersect (non-trivially) with `soln_filter` (if provided),
      - and the combination of token interval & membership set is unique.
    """

    atom_list = sorted(atom_list, key=lambda a: a.get(persp_id).start_token)

    if soln_filter is None:
        matching_solns = [list({a.soln_id for a in a.entries}) for a in atom_list]
        all_matching_solns = set(chain(*matching_solns))
        soln_filter = all_matching_solns
    else:
        soln_filter = set(soln_filter).union({persp_id})

    def atom_memberships(atom):
        # using original_segid here because it makes more sense
        # while still applying the soln_filter
        return set(e.original_segid for e in atom.entries if e.soln_id in soln_filter)

    seen_memberset_endings = defaultdict(lambda : [])
    last_membership = frozenset({})
    n = len(atom_list)

    for start in range(n):
        memberships = atom_memberships(atom_list[start])

        if neg_filter and min(atom_list[start].solution_members()) < 0:
            continue

        # curr_start_token = atom_list[start].get(persp_id).start_token
        # curr_end_token = atom_list[start].get(persp_id).end_token
        curr_memberships = frozenset(memberships.copy())
        
        if start <= max(seen_memberset_endings[frozenset(curr_memberships)], default=-1):
            # we've already seen an ending with these members in the future, so we are within old seg --> skip
            continue

        # extend until we see loss of a member
        for end in range(start+1, n):
            lost_seg_members = curr_memberships.difference(atom_memberships(atom_list[end]))
            if len(lost_seg_members) > 0:
                seen_memberset_endings[curr_memberships].append(end-1)
                yld_seq = [a.filter_solutions(soln_filter) for a in atom_list[start:end]]
                yield yld_seq, list(set.union(*[set(a.solution_members()) for a in yld_seq]))

                curr_memberships = curr_memberships.difference(lost_seg_members)
        else:
            end = min(start+1,n)
            seen_memberset_endings[curr_memberships].append(end)
            yld_seq = [a.filter_solutions(soln_filter) for a in atom_list[start:end]]
            yield yld_seq, list(set.union(*[set(a.solution_members()) for a in yld_seq]))


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
    
    # return np.array(embedding)


def codeemb_filter_atom(persp_id: int, atm, ttrace, tcmp, cutoff=0.95, timeout=60, cached_embeddings=dict()):

    
    
    ttt = {
        k: v
        for k,v in simple_atom_substrs(atm, ttrace, tcmp).items()
    }
    ttk = list(ttt.keys())
    ttv = [ttt[k] for k in ttk]
    tte = get_openai_embeddings(ttv, cached_embeddings=cached_embeddings)
    ttt = {k: e for k, e in zip(ttk, tte)}
    
    refiltered_solns = []
    for k in ttt.keys():
        if ttt[persp_id].shape != ttt[k].shape:
            continue
        if cosine_sim(ttt[persp_id], ttt[k]) < cutoff:
            continue
        else:
            refiltered_solns.append(k)
    
    return atm.filter_solutions(refiltered_solns)


def calc_atom_codeembsim(persp_id: int, atm, ttrace, tcmp, timeout=60, cached_embeddings=dict()):    
    
    ttt = {
        k: v
        for k,v in simple_atom_substrs(atm, ttrace, tcmp).items()
    }
    ttk = list(ttt.keys())
    ttv = [ttt[k] for k in ttk]
    tte = get_openai_embeddings(ttv, cached_embeddings=cached_embeddings)
    ttt = {k: e for k, e in zip(ttk, tte)}
    
    simsc = dict()
    for k in ttt.keys():
        if ttt[persp_id].shape != ttt[k].shape:
            simsc[k] = 0.
        else:
            simsc[k] = cosine_sim(ttt[persp_id], ttt[k])
    return simsc

def glom_cont_segments(seg_ls):
    seg_ls = [s for s in seg_ls if s is not None]
    if seg_ls == []:
        return None
    min_st = min(map(lambda x: x.start_token, seg_ls))
    max_en = max(map(lambda x: x.end_token, seg_ls))
    new_seg = SolutionSegment(seg_ls[0].soln_id, seg_ls[0].soln_length, min_st, max_en)
    if len({ss.original_segid for ss in seg_ls}) == 1:
        new_seg.original_segid = seg_ls[0].original_segid
    return new_seg




## new rolling cached approach

class ClusteredSegmentsMap:
    def __init__(self):
        self._soln_map = defaultdict(lambda : [])
        self._segset_map = defaultdict(lambda : [])
    
    def add(self, atm):
        segset = frozenset(atm.originalseg_members())
        solns = atm.solution_members()

        # doing a naive check for match collisions - latest member addition should be highest trace_id
        # therefore, can check for existing subset clusters by checking if we have segset \ last_id
        last_id = max(solns)
        all_other_ids = list(set(solns).difference({last_id}))
        _sub_segset = frozenset(atm.filter_solutions(all_other_ids).originalseg_members())

        if len(_sub_segset)>1 and _sub_segset in self._segset_map.keys():

            # checking for any cluster that has the same length and sequence matching for some member seq
            for sa_idx, sub_atm in reversed(list(enumerate(self._segset_map[_sub_segset]))):
                _other_idx = sub_atm.solution_members().pop()
                a, b = atm.get(_other_idx), sub_atm.get(_other_idx)
                if a.start_token == b.start_token and a.end_token == b.end_token:
                    # can conclude we want to remove sub_atm because its strongly dominated by the new atm
                    del self._segset_map[_sub_segset][sa_idx]

        # now merge in the latest new atom
        for soln_id in solns:
            self._soln_map[soln_id] = list(set(self._soln_map[soln_id]+[atm]))
        self._segset_map[segset] = list(set(self._segset_map[segset]+[atm]))
    
    def extend(self, atms):
        for atm in atms:
            self.add(atm)
    
    def find_solution(self, soln_id):
        self._soln_map.get(soln_id)
    
    def find_segset(self, segset):
        self._segset_map.get(frozenset(segset))


class IdeaExtractorCache:
    def __init__(self, ps, **kwargs):

        self._all_template_comparisons = dict()
        self._tcmp = {
            'submissions': dict(),
            'comparisons': dict(),
            'matchcounts': dict()
        }
        # TODO: register the template program
        self._template_program = ps.template

        self._soln_atoms = defaultdict(lambda : [])

        self._clustered_segments = ClusteredSegmentsMap() # defaultdict(lambda : [])

        self.ignore_jplagapi_status = kwargs.get('ignore_jplagapi_status', True)
        self.min_match_tokens = kwargs.get('min_match_tokens', 6)
        self.min_match_members = kwargs.get('min_match_members', 3)
        self.min_match_embeddingsim = kwargs.get('min_match_embeddingsim', 0.90)


    def _update_jplag(self, new_soln, ttrace, solution_id_filter=None):
        
        new_soln_id = new_soln.trace_id
        new_soln_idst = str(new_soln.trace_id)

        # update template matches
        ttcmp = clean_compare_many(
            min_token_match=1, ignore_api_status=self.ignore_jplagapi_status,
            **{"-1": self._template_program, new_soln_idst: new_soln.program}
        )
        self._tcmp['comparisons'].update(ttcmp['comparisons'])
        self._tcmp['submissions'].update(ttcmp['submissions'])
    


        # identify clique of new solutions to be compared to the new solution
        if solution_id_filter is None:
            compare_idxs = [a.trace_id for a in ttrace.list]
        else:
            compare_idxs = solution_id_filter


        all_progs = {str(k): ttrace[k].program for k in compare_idxs}
        all_progs.update({new_soln_idst: new_soln.program, })

        if len(all_progs) == 1:
            self._tcmp['submissions'][new_soln_id] = ttcmp['submissions'][new_soln_id]
            return ttcmp['comparisons']

        tcmp = clean_compare_many(min_token_match=self.min_match_tokens, ignore_api_status=self.ignore_jplagapi_status, **all_progs)

        self._tcmp['submissions'][new_soln_id] = tcmp['submissions'][new_soln_id]
        new_comparisons = {
            (a,b):v for (a,b),v in tcmp['comparisons'].items() if a==new_soln_id or b==new_soln_id
        }
        self._tcmp['comparisons'].update(new_comparisons)

        # make sure to include comparisons against template -1
        new_comparisons.update(ttcmp['comparisons'])
        return new_comparisons
    
    def _update_atoms(self, new_persp_id, new_comparisons=None):

        new_id_submd = self._tcmp['submissions'][new_persp_id]

        self._soln_atoms[new_persp_id] = [MatchAtom(entries=[
                SolutionSegment(new_persp_id, soln_length=new_id_submd['numberOfTokens'], start_token=0, end_token=new_id_submd['numberOfTokens']-1)
            ])]
        
        if new_comparisons is not None:
            soln_segms = new_comparisons
        else:
            soln_segms = {(fn, sn): segm for (fn, sn), segm in self._tcmp['comparisons'].items()}

        affected_soln_ids = { new_persp_id }
        for (fn, sn), segm in soln_segms.items():
            for segm_match in segm['matches']:
                new_atom = MatchAtom(entries=[
                    SolutionSegment(
                        fn,
                        soln_length=self._tcmp['submissions'][fn]['numberOfTokens'],
                        start_token=segm_match['startOfFirst'],
                        end_token=min(segm_match['startOfFirst']+segm_match['length']-1, self._tcmp['submissions'][fn]['numberOfTokens']-1),
                        original_segid=segm_match['id']
                    ),
                    SolutionSegment(
                        sn,
                        soln_length=self._tcmp['submissions'][sn]['numberOfTokens'],
                        start_token=segm_match['startOfSecond'],
                        end_token=min(segm_match['startOfSecond']+segm_match['length']-1, self._tcmp['submissions'][sn]['numberOfTokens']-1),
                        original_segid=segm_match['id']
                    ),
            
                ])
                # print(new_atom)
                self._soln_atoms[fn] = marginal_atomize_match(
                    fn,
                    self._soln_atoms[fn],
                    new_atom
                )
                self._soln_atoms[sn] = marginal_atomize_match(
                    sn,
                    self._soln_atoms[sn],
                    new_atom
                )
                affected_soln_ids = affected_soln_ids.union({fn, sn})
        
        return list(affected_soln_ids)



    def persp_idea_segment_extraction(self, persp_id, ttrace, engine, exclude_template=True, min_token_len=7, min_members=4, ce_cutoff=0.90, soln_filter=None, cached_embeddings=None):
        if cached_embeddings is None:
            cached_embeddings=dict()
        
        soln_atoms = self._soln_atoms
        tcmp = self._tcmp
        
        valid_subsegs = defaultdict(lambda : [])
        
        print(persp_id)
        seg_atoms = []
        _soln_filter = list(set(soln_filter).union({-1}))
        for yidx, (seg_subatoms, seg_members) in enumerate(distinct_subsegments(soln_atoms[persp_id], persp_id, soln_filter=_soln_filter, neg_filter=True)):
        
            # FILTER :: ignore atoms that match to the template, we only want novel contributions
            if exclude_template and -1 in chain(*[a.solution_members() for a in seg_subatoms]):
                continue
        
            # TODO: decide if we want to allow supersets of template func
            # if min([e.start_token for e in seg_subatoms[0].entries]) == 0:
            #     raise Exception('wtf stop')

            ## FILTER :: dont include short token matches
            segm_len = sum([a.token_length() for a in seg_subatoms])
            if segm_len < min_token_len:
                print(f'\tfiltering too short segment {segm_len}<{min_token_len}')
                continue
        
            ## FILTER :: dont include matches that have too few members
            if len(seg_members) < min_members:
                print(f'\tfiltering not enough seg_members {len(seg_members)}<{min_members}')
                continue
            
            # collect all segments in the same sequence into a new atom class
            glommed_segs = []
            for m in seg_members:
                if m == -1:
                    continue  # never add in the original problemspec template

                m_segs = [a.get(m) for a in seg_subatoms]
                glom_seg = glom_cont_segments(m_segs)
                glommed_segs.append( glom_seg )

            glommed_segs = [s for s in glommed_segs if s is not None]
            seg_atom = MatchAtom(glommed_segs)

            ## filter atom down to own matches at least 95% codemb with node_idx
            seg_atom = codeemb_filter_atom(persp_id, seg_atom, ttrace, tcmp, cutoff=ce_cutoff, cached_embeddings=cached_embeddings)
            if len(seg_atom.solution_members()) < min_members:
                continue

            ## we now believe this is worth scraping. Use the engine to scrape out meaningful semantic clusters
            distilled_clusters: DistilledIdeaClusters = distill_atom_clusters(seg_atom, ttrace, engine, tcmp)
            for cluster_mems, cluster_desc in distilled_clusters.entries.items():
                
                if len(cluster_mems) < min_members:
                    continue
                
                # we are now finally satisfied with the overlapping sequences being meaningfully similar. append to results list
                seg_atoms.append(seg_atom.filter_solutions(cluster_mems).set_description(cluster_desc))
        return seg_atoms




    def _scrape_idea_segments(self, persp_id, ttrace, engine, affected_soln_ids=None):
        new_segments = self.persp_idea_segment_extraction(
                persp_id, ttrace, engine,
                exclude_template=True, min_token_len=self.min_match_tokens, min_members=self.min_match_members, ce_cutoff=self.min_match_embeddingsim,
                soln_filter=list(affected_soln_ids),
                cached_embeddings=None
            )


        ## TODO: implement resolution logic here for folding together new and old detected segments
        pass



        self._clustered_segments.extend( new_segments )
        return new_segments
    

    def hook(self, ttrace, engine: EngineV3, solution_id_filter=None):
        # we should have exactly one new solution
        print(f"HOOKUP {len(ttrace.list)}")
        new_soln = ttrace.list[-1]
        new_soln_id = new_soln.trace_id


        new_comparisons = self._update_jplag(new_soln, ttrace, solution_id_filter=solution_id_filter)
        affected_soln_ids = self._update_atoms(new_persp_id=new_soln_id, new_comparisons=new_comparisons)
        new_segments = self._scrape_idea_segments(persp_id=new_soln_id, ttrace=ttrace, engine=engine, affected_soln_ids=affected_soln_ids)

        return


