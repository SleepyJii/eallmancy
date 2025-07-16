
import numpy as np
from typing import Optional, List
from dataclasses import dataclass
from trace_analysis.segm_printing import *


@dataclass
class SolutionSegment:
    soln_id: int
    soln_length: int   # number of tokens in soln as per JPlag
    start_token: int
    end_token: int     # INCLUSIVE!!!
    original_segid: Optional[int] = None

    def __hash__(self):
        # specifically not including original_segid, because I want to prefer pre-existing None
        return hash(f'{self.soln_id},{self.soln_length},{self.start_token},{self.end_token}')

    def __eq__(self, oth):
        return self.__hash__() == oth.__hash__()
    
    def copy(self):
        return SolutionSegment(self.soln_id, self.soln_length, self.start_token, self.end_token, self.original_segid)
    
    @property
    def length(self): return 1 + self.end_token - self.start_token

    @property
    def is_valid(self):
        return (self.start_token >= 0) and (self.end_token >= self.start_token) and (self.end_token < self.soln_length)

    def set_start_token(self, idx):
        self.start_token = idx
        return self
    
    def set_end_token(self, idx):
        self.end_token = idx
        return self

@dataclass
class MatchAtom:
    entries: List[SolutionSegment]
    description: Optional[str] = None

    def _filter_invalid(self):
        for e in self.entries:
            if not e.is_valid:
                raise Exception("why are we invalidating?")
            #     print('invalidating',e)
        self.entries = [e for e in self.entries if e.is_valid]
        return self

    def __post_init__(self):
        self._filter_invalid()

    def __hash__(self):
        # specifically not including original_segid, because I want to prefer pre-existing None
        return hash(frozenset({e.__hash__() for e in self.entries}))

    def __eq__(self, oth):
        return self.__hash__() == oth.__hash__()

    def get(self, perspective_id: int):
        rr = [e for e in self.entries if e.soln_id == perspective_id]
        if len(rr) > 0:
            return rr.pop()
        return None

    def solution_members(self):
        return set([e.soln_id for e in self.entries])

    def originalseg_members(self):
        return set([e.original_segid for e in self.entries])

    def token_length(self):
        if len(self.entries) == 0:
            return 0
        for e in self.entries:
            break
        return e.length

    def set_description(self, sstr):
        self.description = sstr
        return self

    def add(self, segment):
        ex = self.get(segment.soln_id)
        if ex is not None:
            if ex.original_segid is None:
                # to be replaced!
                self.entries = [e for e in self.entries if e!=ex] + [segment]
                return self
        self.entries.append(segment)
        self.entries = list(set(self.entries))
        return self

    def extend(self, atom):
        self.entries.extend(atom.entries)
        self.entries = list(set(self.entries))
        return self

    def set(self, perspective_id: int, start_token: Optional[int] = None, end_token: Optional[int] = None):
        perspective_segment = self.get(perspective_id)
        
        if start_token is not None:
            drift = start_token - perspective_segment.start_token
            self.entries = [e.set_start_token(e.start_token + drift) for e in self.entries]
        
        if end_token is not None:
            drift = end_token - perspective_segment.end_token
            self.entries = [e.set_end_token(e.end_token + drift) for e in self.entries]

        self._filter_invalid()
        return self

    def split(self, persp_id, splitidx):  # NB, splitidx inclusive to LEFT
        return self.copy().set(persp_id, end_token=splitidx), self.copy().set(persp_id, start_token=splitidx+1)
    
    def copy(self):
        return MatchAtom(entries=[e.copy() for e in self.entries])

    def filter_solutions(self, allowed_soln_ids):
        return MatchAtom(
            [e.copy() for e in self.entries if e.soln_id in allowed_soln_ids]
        )

    @property
    def is_empty(self):
        return len(self.entries) == 0

def marginal_atomize_match(persp_id: int, existing_matches: List[MatchAtom], new_atom: MatchAtom):

    merging_atoms = [new_atom]
    while merging_atoms != []:
        new_atom = merging_atoms.pop()
        if new_atom.is_empty:
            continue
        
        new_atoms = []
        for eidx, e_matchatom in enumerate(existing_matches):
            e_segment = e_matchatom.get(persp_id)
            new_segment = new_atom.get(persp_id)

            if e_segment is None or new_segment is None:
                continue
            
            if new_segment.start_token > e_segment.end_token or new_segment.end_token < e_segment.start_token:
                continue

            if new_segment.start_token < e_segment.start_token:

                # splitatom_b, splitatom_c = e_matchatom.split(new_segment.soln_id, new_segment.end_token)
                merging_atoms.append( new_atom.copy().set(persp_id, start_token=e_segment.start_token) )
                merging_atoms.append( new_atom.copy().set(persp_id, end_token=e_segment.start_token-1) )
                new_atoms = existing_matches #unchanged
                # print('\t',1)
                break # force loop restart
                
            elif new_segment.start_token > e_segment.start_token:
                splitatom_b, splitatom_c = e_matchatom.split(new_segment.soln_id, new_segment.start_token-1)
                merging_atoms.append( new_atom )
                new_atoms.extend(existing_matches[:eidx]+[splitatom_b, splitatom_c]+existing_matches[eidx+1:])
                # print('\t',2)
                break
                
            else:
                # start tokens match, consider end tokens
                if new_segment.end_token < e_segment.end_token:
    
                    splitatom_b, splitatom_c = e_matchatom.split(new_segment.soln_id, new_segment.end_token)
                    merging_atoms.append( new_atom )
                    new_atoms.extend(existing_matches[:eidx]+[splitatom_b, splitatom_c]+existing_matches[eidx+1:])
                    # print('\t',3)
                    break
                    
                elif new_segment.end_token > e_segment.end_token:
                    merging_atoms.append( new_atom.copy().set(persp_id, end_token=e_segment.end_token) )
                    merging_atoms.append( new_atom.copy().set(persp_id, start_token=e_segment.end_token+1) )
                    new_atoms = existing_matches #unchanged
                    # print('\t',4)
                    break
            
                else:
                    # must have equality
                    e_matchatom.extend(new_atom)
                    new_atoms = existing_matches
                    # print('\t',5)
                    break
        else:
            # new segment has no overlap with existing atoms
            new_atoms = existing_matches
            new_atoms.append(new_atom)

        existing_matches = new_atoms

    return [em for em in existing_matches if em.get(persp_id) is not None]



def build_atomized_segments(tcmp):
    
    soln_atoms = {
        nn: [MatchAtom(entries=[
            SolutionSegment(nn, soln_length=nndd['numberOfTokens'], start_token=0, end_token=nndd['numberOfTokens']-1)
        ])]
        for nn, nndd in tcmp['submissions'].items()
    }
    soln_segms = {idx: segmddx for idx, segmddx in tcmp['comparisons'].items()}
    for (fn, sn), segm in tcmp['comparisons'].items():
        for segm_match in segm['matches']:
            new_atom = MatchAtom(entries=[
                SolutionSegment(
                    fn,
                    soln_length=tcmp['submissions'][fn]['numberOfTokens'],
                    start_token=segm_match['startOfFirst'],
                    end_token=segm_match['startOfFirst']+segm_match['length']-1,
                    original_segid=segm_match['id']
                ),
                SolutionSegment(
                    sn,
                    soln_length=tcmp['submissions'][sn]['numberOfTokens'],
                    start_token=segm_match['startOfSecond'],
                    end_token=segm_match['startOfSecond']+segm_match['length']-1,
                    original_segid=segm_match['id']
                ),
        
            ])
            # print(new_atom)
            soln_atoms[fn] = marginal_atomize_match(
                fn,
                soln_atoms[fn],
                new_atom
            )
            soln_atoms[sn] = marginal_atomize_match(
                sn,
                soln_atoms[sn],
                new_atom
            )
    return soln_atoms, soln_segms



