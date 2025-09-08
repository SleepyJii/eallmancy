
from abc import ABC, abstractmethod

import requests
import backoff
import numpy as np
from collections import defaultdict
import itertools
from itertools import chain, count
import os
import re
from typing import Dict, List


from eallmancy.analysis.jplag.jplag_api_interface import clean_compare_many
from eallmancy.analysis.analyzer.utils import get_openai_embeddings, cosine_sim
from eallmancy.analysis.analyzer.tokenstr_handling import simple_segm_substr, grab_programbody
from eallmancy.analysis.analyzer.atomization import MatchAtom, SolutionSegment, marginal_atomize_match
from eallmancy.analysis.analyzer.pairwise_trace_analysis import PairwiseTraceAnalysis
from eallmancy.analysis.analyzer.cluster_trace_analysis import ClusterTraceAnalysis
from eallmancy.analysis.analyzer.segment_trace_analysis import SegmentTraceAnalysis


def re_extract(ptrn, sstr, typecast=str):
    sres = re.findall(ptrn, sstr)
    if len(sres) == 0:
        return None
    return typecast(sres[0])


def _match_to_solutionsegment(n, segm_match, tcmp, first=True):
    if first:
        return SolutionSegment(
            n,
            soln_length=tcmp['submissions'][n]['numberOfTokens'],
            start_token=segm_match['startOfFirst'],
            end_token=min(segm_match['startOfFirst']+segm_match['length']-1, tcmp['submissions'][n]['numberOfTokens']-1),
            # original_segid=segm_match['id']
        )
    else:
        return SolutionSegment(
            n,
            soln_length=tcmp['submissions'][n]['numberOfTokens'],
            start_token=segm_match['startOfSecond'],
            end_token=min(segm_match['startOfSecond']+segm_match['length']-1, tcmp['submissions'][n]['numberOfTokens']-1),
            # original_segid=segm_match['id']
        )



class Analyzer:

    ignore_jplagapi_status = True
    min_match_tokens = 6


    @classmethod
    def _calc_jplag(cls, ps, trace):

        # _template_program = ps.template
        
        _tcmp = {
                    'submissions': dict(),
                    'comparisons': dict(),
                    'matchcounts': dict()
                }

        # now calculate overlaps for everything else with a sane min_token
        all_progs = {
            str(a.trace_id): grab_programbody(a.program)
            for a in trace.list if a.is_solution
        }
        tcmp = clean_compare_many(
            min_token_match=cls.min_match_tokens,
            ignore_api_status=cls.ignore_jplagapi_status, **all_progs
        )
        _tcmp['submissions'].update(tcmp['submissions'])
        _tcmp['comparisons'].update(tcmp['comparisons'])

        invalid_solns = set(map(int, all_progs.keys())).difference(set(_tcmp['submissions'].keys()))

        return _tcmp, invalid_solns


    @classmethod
    def _cleanup_matches(cls, trace, tcmp):
        new_tcmp = {
            'submissions': tcmp['submissions'],
            'comparisons': dict()
        }
        for fn, sn in tcmp['comparisons'].keys():
            matches = tcmp['comparisons'][(fn, sn)]['matches']
            valid_matches = []
            for segm_match in matches:
                fs = _match_to_solutionsegment(fn, segm_match, tcmp, first=True)
                ss = _match_to_solutionsegment(sn, segm_match, tcmp, first=False)
                
                if fs.length == ss.length:
                    segm_strings = [simple_segm_substr(trace, fs, tcmp), simple_segm_substr(trace, ss, tcmp)]
                    if '' in segm_strings:
                        continue
                    valid_matches.append(segm_match)
            new_tcmp['comparisons'][(fn, sn)] = {k:v for k,v in tcmp['comparisons'][(fn, sn)].items() if k!='matches'}
            new_tcmp['comparisons'][(fn, sn)]['matches'] = valid_matches
        return new_tcmp

    @classmethod
    def _add_match_similarities_batched(cls, trace, tcmp):
        new_tcmp = {
            'submissions': tcmp['submissions'],
            'comparisons': dict()
        }

        to_run = []
        for fn, sn in tcmp['comparisons'].keys():
            matches = tcmp['comparisons'][(fn, sn)]['matches']
            valid_matches = []
            for match_id, segm_match in enumerate(matches):
                fs = _match_to_solutionsegment(fn, segm_match, tcmp, first=True)
                ss = _match_to_solutionsegment(sn, segm_match, tcmp, first=False)
                segm_strings = [simple_segm_substr(trace, fs, tcmp), simple_segm_substr(trace, ss, tcmp)]
                to_run.append((*segm_strings, fn, sn, match_id))

        batch_size=300
        for b_start in range(0, len(to_run), batch_size):
            batch_runs = to_run[b_start:min(b_start+batch_size, len(to_run))]
            all_embds = get_openai_embeddings(list(chain(*[[e[0], e[1]] for e in batch_runs])))
            print(f'recv batch {b_start}-{b_start+len(batch_runs)}')
            for idx, _ in enumerate(all_embds):
                if idx % 2 != 0:
                    continue
                fs_embed, ss_embed = all_embds[idx], all_embds[idx+1]
                fs_str, ss_str, fn, sn, match_id = batch_runs[idx//2]
                tcmp['comparisons'][(fn, sn)]['matches'][match_id]['cosine_sim'] = cosine_sim(fs_embed, ss_embed)

        return tcmp

    @classmethod
    def _add_fallback_similarities_batched(cls, trace, tcmp, invalid_solns):
        # we want every 
        to_run = [(a, grab_programbody(trace[a].program)) for a in invalid_solns]
        embs = dict()

        batch_size=300
        for b_start in range(0, len(to_run), batch_size):
            batch_runs = to_run[b_start:min(b_start+batch_size, len(to_run))]
            all_embds = get_openai_embeddings([prg for _, prg in batch_runs])
            print(f'recv batch {b_start}-{b_start+len(batch_runs)}')
            for (k,_), emb in zip(batch_runs, all_embds):
                embs[k] = emb
        
        aaa = list(sorted(invalid_solns))
        dsts = dict()
        for a_idx, a in enumerate(aaa[:-1]):
            for b in aaa[a_idx+1:]:
                dsts[(a,b)] = cosine_sim(all_embds[a], all_embds[b])

        return dict(
            submissions=tcmp['submissions'],
            comparisons=tcmp['comparisons'],
            fallbacks=dsts
        )


    @classmethod
    def build_pairwise_analysis(cls, trace, ps):
        
        # get JPlag metrics as before
        _tcmp, invalid_solns = Analyzer._calc_jplag(ps, trace)

        _tcmp = Analyzer._cleanup_matches(trace, _tcmp)

        # now we diverge a bit. we want to calculate cosine similarity per comparison.
        _tcmp = Analyzer._add_match_similarities_batched(trace, _tcmp)

        return PairwiseTraceAnalysis(ps, _tcmp, invalid_solns)


    # ANALYZER AS CLASS

    def __init__(self, trace, cached_tcmp=None, invalid_solns=set()):
        
        if cached_tcmp is None:
            # get JPlag metrics as before
            _tcmp, invalid_solns = Analyzer._calc_jplag(trace.problem_spec, trace)
            _tcmp = Analyzer._cleanup_matches(trace, _tcmp)
            # now we diverge a bit. we want to calculate cosine similarity per comparison.
            self._tcmp = Analyzer._add_match_similarities_batched(trace, _tcmp)
            self._tcmp = Analyzer._add_fallback_similarities(trace, _tcmp, invalid_solns)
            self._invalid_solns=invalid_solns
        else:
            self._tcmp = cached_tcmp
            self._invalid_solns=invalid_solns
        self._trace = trace

    def distance(self, *args, **kwargs):
        return PairwiseTraceAnalysis(ps, self._tcmp, invalid_solns=self._invalid_solns).distance(*args, **kwargs)
    
    def cluster_analysis(self, cluster_traceids):
        return ClusterTraceAnalysis(cluster_traceids, trace=self._trace, tcmp=self._tcmp, invalid_solns=self._invalid_solns)
    
    def segment_analysis(self, **kwargs):
        return SegmentTraceAnalysis(trace=self._trace, tcmp=self._tcmp, invalid_solns=self._invalid_solns, **kwargs)

