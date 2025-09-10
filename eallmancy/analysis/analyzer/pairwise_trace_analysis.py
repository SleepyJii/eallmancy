
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




class PairwiseTraceAnalysis:
    def __init__(self, ps, tcmp, invalid_solns=set()):
        self._ps = ps
        self._tcmp = tcmp
        self._invalid_solns=invalid_solns

    def distance(self, solna, solnb, emb_mode='weight'):
        if solna.trace_id == solnb.trace_id:
            return 0.0

        if (min(solna.trace_id, solnb.trace_id),max(solna.trace_id, solnb.trace_id)) not in self._tcmp['comparisons']:
            return 1.0  # idk why these arent here

        if (solna.trace_id in self._invalid_solns) and (solnb.trace_id in self._invalid_solns):
            # SPECIAL SUBROUTINE - DIRECT COSINE SIMILARITY
            return 1.0  # programs too short to compare are considered nonmatching

        cutoff_thresh = re_extract(r'cutoff\(([0-9,\.]+)\)', emb_mode, typecast=float)

        # find ideas overlap
        ab_compare = self._tcmp['comparisons'][(min(solna.trace_id, solnb.trace_id),max(solna.trace_id, solnb.trace_id))]

        # can just use A, we must be matching on same number of tokens anyway
        f_idx = ab_compare['first_idx']
        hasmatch_memo = np.zeros((self._tcmp['submissions'][f_idx]['numberOfTokens'],))

        for smatch in ab_compare['matches']:
            segm = _match_to_solutionsegment(f_idx, smatch, self._tcmp, first=True)

            if emb_mode.lower().startswith('cutoff'):
                if (1-smatch['cosine_sim']) <= cutoff_thresh:
                    # consider the jplag match valid
                    hasmatch_memo[segm.start_token:segm.end_token+1] = 1.0
            elif emb_mode.lower() == 'weight':
                # weight the jplag match by cosine sim
                hasmatch_memo[segm.start_token:segm.end_token+1] = smatch['cosine_sim']
            elif emb_mode.lower() == 'ignore':
                # recr jplag dist
                hasmatch_memo[segm.start_token:segm.end_token+1] = 1.0
            else:
                raise Exception(f'unknown emb_mode: {emb_mode}, expected cutoff(*)|weight|ignore')

        a_tokenlen = self._tcmp['submissions'][solna.trace_id]['numberOfTokens']
        b_tokenlen = self._tcmp['submissions'][solnb.trace_id]['numberOfTokens']
        return 1 - (hasmatch_memo.sum() * (0.5 / a_tokenlen + 0.5 / b_tokenlen))

