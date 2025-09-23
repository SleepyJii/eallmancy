
import numpy as np
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from eallmancy.analysis.analyzer.utils import get_openai_embeddings
from eallmancy.analysis.analyzer.atomization.solution_segment import SolutionSegment
from eallmancy.analysis.analyzer.utils import cosine_sim


@dataclass
class MatchAtom:
    entries: List[SolutionSegment]
    description: Optional[str] = None
    # cache: Optional[Dict] = field(default_factory=dict)

    def _filter_invalid(self):
        # for e in self.entries:
        #     if not e.is_valid:
        #         raise Exception("why are we invalidating?")  # TODO: remove, leaving this here for debugging.
            #     print('invalidating',e)
        self.entries = [e for e in self.entries if e.is_valid]

        lens = [s.length for s in self.entries]
        if max(lens) != min(lens):
            raise Exception('length mismatch in atom. we aint having it anymore')
        if max(lens) > np.ceil(1.5*min(lens)):
            raise Exception('Crazy length mismatch within atom!')

        return self

    def __post_init__(self):
        self._filter_invalid()

    def __hash__(self):
        # specifically not including original_segid, because I want to prefer pre-existing None
        return hash(frozenset({e.__hash__() for e in sorted(self.entries, key=lambda e: e.soln_id)}))

    def __eq__(self, oth):
        return self.__hash__() == oth.__hash__()
    
    # def _reset_cache(self):
    #     self.cache = dict()

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
        return MatchAtom(entries=[e.copy() for e in self.entries], description=self.description,
        #  cache={k:v for k,v in self.cache.items()}
        )

    def filter_solutions(self, allowed_soln_ids, reset_cache=True):
        return MatchAtom(
            [e.copy() for e in self.entries if e.soln_id in allowed_soln_ids],
            # cache=dict() if reset_cache else self.cache.copy()
        )
    
    @property
    def length(self):
        if self.is_empty:
            return 0
        return self.entries[0].length

    @property
    def is_empty(self):
        return len(self.entries) == 0

