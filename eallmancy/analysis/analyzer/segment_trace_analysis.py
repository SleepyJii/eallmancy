
from abc import ABC, abstractmethod

import requests
import backoff
import numpy as np
from collections import defaultdict, Counter
import itertools
from itertools import chain, count
import os
import re
from typing import Dict, List, Set
from dataclasses import dataclass
from functools import reduce


from eallmancy.analysis.jplag.jplag_api_interface import clean_compare_many
from eallmancy.analysis.analyzer.utils import get_openai_embeddings, cosine_sim
from eallmancy.analysis.analyzer.tokenstr_handling import simple_segm_substr, grab_programbody
from eallmancy.analysis.analyzer.atomization import MatchAtom, SolutionSegment, marginal_atomize_match
from eallmancy.analysis.analyzer.segmentation import distinct_subsegments


@dataclass
class SparseProgramTemplate:
    atoms: Set[MatchAtom]

    def __post_init__(self):
        # double check all memberships are identical
        uniq_memberships = set(frozenset(a.solution_members()) for a in self.atoms)
        if len(uniq_memberships) > 1:
            raise Exception("attempted to create SparseProgramTemplate from atoms with varying memberships")
        elif len(self.atoms) == 0:
            raise Exception("attempted to create empty SparseProgramTemplate")

    def token_length(self):
        return min(map(lambda atm: atm.token_length(), self.atoms))
    
    def solution_members(self):
        return list(self.atoms)[0].solution_members()
    
    def get(self, soln_idx):
        return list(sorted([a.get(soln_idx) for a in atoms], key=lambda sgm: sgm.start_token))


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


def glom_cont_segments(seg_ls):
    seg_ls = [s for s in seg_ls if s is not None]
    if seg_ls == []:
        return None
    min_st = min(map(lambda x: x.start_token, seg_ls))
    max_en = max(map(lambda x: x.end_token, seg_ls))
    new_seg = SolutionSegment(seg_ls[0].soln_id, seg_ls[0].soln_length, min_st, max_en)

    return new_seg


def _codeemb_split_atm(atm, persp_id, thresh=0.95, verbose=False):
    # first, cut down everything that doesnt match persp_id segment to threshold
    persp_segm = atm.get(persp_id)
    valid_entries = [
        e for e in atm.entries
        if (cosine_sim(persp_segm.embedding, e.embedding)>=thresh) and e.soln_id!=persp_id
    ]
    if verbose:
        print(thresh, [[cosine_sim(_e.embedding, e.embedding) for _e in [persp_segm]+valid_entries] for e in [persp_segm]+valid_entries])
    clusters = []
    for segm in valid_entries:
        for c_idx, cl in enumerate(clusters):
            if not any([cosine_sim(segm.embedding, mem.embedding) < thresh for mem in cl]):
                clusters[c_idx].append(segm)
                break
        else:
            clusters.append([segm])  # new cluster
    res = [MatchAtom(cl+[persp_segm]) for cl in clusters]
    # print(f'\t\t\treturning {len(res)} atms')
    return res




class SegmentTraceAnalysis:

    def _build_atoms(self, tcmp):
        def _tid_subm(tid):
                return tcmp['submissions'][tid]
        _solns = set(tcmp['submissions'].keys()).intersection([s.trace_id for s in self._trace.list if s.is_solution])
        if self.verbose: print('SOLNS', _solns)
        _atoms = {
            tid: [
                MatchAtom(entries=[
                    SolutionSegment(tid, soln_length=_tid_subm(tid)['numberOfTokens'], start_token=0, end_token=_tid_subm(tid)['numberOfTokens']-1)
                ])
            ]
            for tid in _solns
        }

        atoms_to_add = []
        for fn, sn in tcmp['comparisons'].keys():
            if fn not in _solns:
                if self.verbose: print('skipping unknown',fn)
                continue
            if sn not in _solns:
                if self.verbose: print('skipping unknown',sn)
                continue
            
            matches = tcmp['comparisons'][(fn, sn)]['matches']
            valid_matches = []
            for match_id, segm_match in enumerate(matches):
                fs = _match_to_solutionsegment(fn, segm_match, tcmp, first=True)
                ss = _match_to_solutionsegment(sn, segm_match, tcmp, first=False)
                new_atom = MatchAtom(entries=[fs, ss]) # (these should have already been length-checked, dont worry about that)

                _atoms[fn] = marginal_atomize_match( fn, _atoms[fn], new_atom )
                _atoms[sn] = marginal_atomize_match( sn, _atoms[sn], new_atom )

        return _atoms


    def glommed_reclustered_atms(self, _atoms, min_token_len=7, min_members=3, ce_cutoff=0.95):
        
        # THIS IS THE FINAL TARGET
        seg_atoms = defaultdict(lambda : [])

        for arte in self._trace.list:
            if not arte.is_solution:
                continue
            persp_id = arte.trace_id
            if self.verbose: print(f'[{persp_id}] CHECKING ATOMS')

            # for batch calling code emb
            to_embcheck_atms = []
                
            for yidx, (seg_subatoms, seg_members) in enumerate(distinct_subsegments(_atoms[persp_id], persp_id)):
            
                ## FILTER :: dont include short token matches
                segm_len = sum([a.token_length() for a in seg_subatoms])
                if segm_len < min_token_len:
                    continue
            
                ## FILTER :: dont include matches that have too few members
                if len(seg_members) < min_members:
                    continue
                
                
                # collect all segments in the same sequence into a new atom class
                glommed_segs = []
                persp_segm = None
                for m in seg_members:

                    m_segs = [a.get(m) for a in seg_subatoms]
                    glom_seg = glom_cont_segments(m_segs)
                    glommed_segs.append( glom_seg )

                    if m == persp_id:
                        persp_segm = glom_seg
                if self.verbose: print(f'\t[{persp_id}]{set(seg_members)}:{persp_segm.start_token}-{persp_segm.end_token}')

                glommed_segs = [s for s in glommed_segs if s is not None]
                # _lns = set([s.length for s in glommed_segs])
                glommed_segs = [s for s in glommed_segs if s.length==glom_seg.length]
                seg_atom = MatchAtom(glommed_segs)

                if len(seg_atom.entries) < min_members:
                    if self.verbose: print(f'\t\tinsuf members after length checks')
                    continue

                to_embcheck_atms.append( seg_atom )
                
            to_embcheck_segms = []
            for a_id, atm in enumerate(to_embcheck_atms):
                for segm in atm.entries:
                    to_embcheck_segms.append((a_id, segm))
            segm_embds = dict()

            batch_size=300
            for b_start in range(0, len(to_embcheck_segms), batch_size):
                batch_segms = to_embcheck_segms[b_start:min(b_start+batch_size, len(to_embcheck_segms))]
                batch_segm_strs = [simple_segm_substr(self._trace, segm, self._tcmp) for _, segm in batch_segms]

                batch_embds = get_openai_embeddings(batch_segm_strs)
                if self.verbose: print(f'\t[P{persp_id}] emb batch {b_start}-{b_start+len(batch_segms)}')
                for (_, segm), embd in zip(batch_segms, batch_embds):
                    segm.set_embedding(embd)

            ## all internal segments should now have embeddings - filter out solutions!
            for atm in to_embcheck_atms:
                # need to recalc code emb clusters... in chronological order
                if atm.get(persp_id) is None:
                    if self.verbose: print(f'\t\tlost persp_id segm for some reason???')
                        
                    continue # idk why this happens, skip
                # else:
                #     print('\t\t[P{persp_id}] unioning atms')
                split_atoms = _codeemb_split_atm(atm, persp_id, thresh=ce_cutoff, verbose=self.verbose)
                for spl_atm in split_atoms:
                    if len(spl_atm.entries) < min_members:
                        if self.verbose: print(f'\t\t{spl_atm.solution_members()} split cluster too small')
                        continue
                    seg_atoms[persp_id].append(spl_atm)
        return seg_atoms

    def collect_atomic_templates(self):
        uniq_membersets = defaultdict(lambda : set())
        for k, atms in self._atoms.items():
            if atms == []:
                continue
            for atm in atms:
                mms = frozenset(atm.solution_members())
                uniq_membersets[mms] = uniq_membersets[mms].union({atm})
        
        _templates = [SparseProgramTemplate(atmls) for atmls in uniq_membersets.values()]
        soln_templates = defaultdict(lambda : [])
        for tt in _templates:
            for s in tt.solution_members():
                soln_templates[s].append(tt)
        return _templates, soln_templates



    def __init__(self, trace, tcmp, invalid_solns=set(), min_tokens=7, emb_cutoff=0.97, min_members=3, verbose=False):
        self._trace = trace
        self._tcmp = tcmp
        self._invalid_solns=invalid_solns
        self.verbose = verbose

        # atomize `cluster_traceids` matches
        _debug_atoms = _atoms = self._build_atoms(tcmp)

        # enhance with embedding distances per match
        self._atoms = self.glommed_reclustered_atms(
            _atoms,
            min_token_len=min_tokens,
            min_members=min_members, 
            ce_cutoff=emb_cutoff
        )
        self.templates, self.soln_templates = self.collect_atomic_templates()
