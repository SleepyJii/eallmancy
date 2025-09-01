
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



class PairwiseTraceAnalysis:
    def __init__(self, ps, tcmp, invalid_solns=set()):
        self._ps = ps
        self._tcmp = tcmp
        self._invalid_solns=invalid_solns

    def distance(self, solna, solnb, emb_mode='weight'):
        if solna.trace_id in self._invalid_solns or solnb.trace_id in self._invalid_solns:
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
    def build_pairwise_analysis(cls, trace, ps):
        
        # get JPlag metrics as before
        _tcmp, invalid_solns = Analyzer._calc_jplag(ps, trace)

        _tcmp = Analyzer._cleanup_matches(trace, _tcmp)

        # now we diverge a bit. we want to calculate cosine similarity per comparison.
        _tcmp = Analyzer._add_match_similarities_batched(trace, _tcmp)

        return PairwiseTraceAnalysis(ps, _tcmp)


    # ANALYZER AS CLASS

    def __init__(self, trace, cached_tcmp=None, invalid_solns=set()):
        
        if cached_tcmp is None:
            # get JPlag metrics as before
            _tcmp, invalid_solns = Analyzer._calc_jplag(trace.problem_spec, trace)
            _tcmp = Analyzer._cleanup_matches(trace, _tcmp)
            # now we diverge a bit. we want to calculate cosine similarity per comparison.
            self._tcmp = Analyzer._add_match_similarities_batched(trace, _tcmp)
            self._invalid_solns=invalid_solns
        else:
            self._tcmp = cached_tcmp
            self._invalid_solns=invalid_solns
        self._trace = trace

    def distance(self, *args, **kwargs):
        return PairwiseTraceAnalysis(ps, self._tcmp).distance(*args, **kwargs)
    
    def cluster_analysis(self, cluster_traceids):
        return ClusterTraceAnalysis(cluster_traceids, trace=self._trace, tcmp=self._tcmp)

