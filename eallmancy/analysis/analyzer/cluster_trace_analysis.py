
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


def _drop_listend_stubatom(atms, tcmp):
    if len(atms) == 0:
        return atms
    elif len(atms[-1].solution_members()) == 1:
        segm = atms[-1].get(atms[-1].solution_members().pop())
        if tcmp['submissions'][segm.soln_id]['tokenList'][segm.end_token]['type'] == 'FILE_END':
            return atms[:-1]
    return atms


class ClusterTraceAnalysis:

    def _build_atoms(self, cluster_traceids, tcmp):
        def _tid_subm(tid):
                return tcmp['submissions'][tid]
        _atoms = {
            tid: [
                MatchAtom(entries=[
                    SolutionSegment(tid, soln_length=_tid_subm(tid)['numberOfTokens'], start_token=0, end_token=_tid_subm(tid)['numberOfTokens']-1)
                ])
            ]
            for tid in cluster_traceids
        }

        atoms_to_add = []
        for fn, sn in tcmp['comparisons'].keys():
            if {fn, sn}.difference(cluster_traceids):
                continue
            matches = tcmp['comparisons'][(fn, sn)]['matches']
            valid_matches = []
            for match_id, segm_match in enumerate(matches):
                fs = _match_to_solutionsegment(fn, segm_match, tcmp, first=True)
                ss = _match_to_solutionsegment(sn, segm_match, tcmp, first=False)
                new_atom = MatchAtom(entries=[fs, ss]) # (these should have already been length-checked, dont worry about that)

                _atoms[fn] = marginal_atomize_match( fn, _atoms[fn], new_atom )
                _atoms[sn] = marginal_atomize_match( sn, _atoms[sn], new_atom )

        for k in _atoms.keys():
            _atoms[k] = _drop_listend_stubatom(_atoms[k], tcmp)
        return _atoms

    def _add_segm_embeddings(self, atoms, trace, tcmp):

        # assuming I can do this all inplace?
        all_atoms = list(chain(*atoms.values()))
        all_segms = list(chain(*map(lambda atm: atm.entries, all_atoms)))

        batch_size=300
        for b_start in range(0, len(all_segms), batch_size):
            batch_segms = all_segms[b_start:min(b_start+batch_size, len(all_segms))]
            batch_segm_strs = [simple_segm_substr(trace, segm, tcmp) for segm in batch_segms]

            batch_embds = get_openai_embeddings(batch_segm_strs)
            print(f'\tbatch {b_start}-{b_start+len(batch_segms)}')
            for segm, embd in zip(batch_segms, batch_embds):
                segm.set_embedding(embd)

        return atoms

    def __init__(self, cluster_traceids, trace, tcmp, invalid_solns=set()):
        self.cluster_traceids = cluster_traceids
        self._trace = trace
        self._tcmp = tcmp
        self._invalid_solns=invalid_solns

        # atomize `cluster_traceids` matches
        _atoms = self._build_atoms(cluster_traceids, tcmp)

        # enhance with embedding distances per match
        self._atoms = self._add_segm_embeddings(_atoms, trace, tcmp)

