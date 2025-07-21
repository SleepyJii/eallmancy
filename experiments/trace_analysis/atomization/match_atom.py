
import numpy as np
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from trace_analysis.atomization.embeddings import get_openai_embeddings
from trace_analysis.atomization.solution_segment import SolutionSegment
from trace_analysis.utils import cosine_sim
from trace_analysis.segm_printing import *



@dataclass
class MatchAtom:
    entries: List[SolutionSegment]
    description: Optional[str] = None
    cache: Optional[Dict] = field(default_factory=dict)

    def _filter_invalid(self):
        # for e in self.entries:
        #     if not e.is_valid:
        #         raise Exception("why are we invalidating?")  # TODO: remove, leaving this here for debugging.
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
    
    def _reset_cache(self):
        self.cache = dict()

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
    
    def update_cache(self, **kwargs):
        self.cache.update(**kwargs)
        return self
    
    @property
    def embedding(self):
        if 'embedding' not in self.cache.keys():
            ttt = {
                k: v
                for k,v in simple_atom_substrs(self, ttrace, tcmp).items()
            }
            ttk = list(ttt.keys())
            ttv = [ttt[k] for k in ttk]
            tte = get_openai_embeddings(ttv, cached_embeddings=cached_embeddings)
            pass
        return self.cache['embedding']



    def filter_embedding_similarity(self, persp_id: int, ttrace, tcmp, cutoff=0.95, timeout=60, cached_embeddings=dict()):
        
        ttt = {
            k: v
            for k,v in simple_atom_substrs(self, ttrace, tcmp).items()
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
        
        return self.filter_solutions(refiltered_solns).update_cache(embedding=sum(ttt[tk] for tk in refiltered_solns) / len(refiltered_solns))



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
    
    def accrete(self, atm):
        # want to combine segments per origin soln
        my_solns = self.solution_members()
        other_solns = atm.solution_members()
        overlap_solns = set(my_solns).intersection(other_solns)
        new_entries = [e for e in self.entries if e.soln_id in my_solns and e.soln_id not in overlap_solns]
        new_entries.extend([e for e in atm.entries if e.soln_id in other_solns and e.soln_id not in my_solns])
        for s in overlap_solns:
            # confirm that relevant entries are overlapping, or raise
            my_seg: SolutionSegment = self.get(s)
            ot_seg: SolutionSegment = atm.get(s)
            if my_seg.start_token > ot_seg.end_token or my_seg.end_token < ot_seg.start_token:
                raise Exception("attempting to accrete disjoint atoms")
            new_entries.append(
                # extended segment
                SolutionSegment(
                    s,
                    my_seg.soln_length,
                    min(my_seg.start_token, ot_seg.start_token),
                    max(my_seg.end_token, ot_seg.end_token),
                    my_seg.original_segid or ot_seg.original_segid
                )
            )
        res = MatchAtom(new_entries, '\n'.join([dsc for dsc in [self.description, atm.description] if dsc is not None]) or None)

        # special condition for code embedding maintenance in cache
        if 'embedding' in self.cache.keys() and 'embedding' in atm.cache.keys():
            res = res.update_cache(embedding=(self.cache['embedding']*len(self.entries) + atm.cache['embedding']*len(atm.entries))/(len(self.entries)+len(atm.entries)))
        
        return res

    def set(self, perspective_id: int, start_token: Optional[int] = None, end_token: Optional[int] = None):
        perspective_segment = self.get(perspective_id)
        
        if start_token is not None:
            drift = start_token - perspective_segment.start_token
            self.entries = [e.set_start_token(e.start_token + drift) for e in self.entries]
        
        if end_token is not None:
            drift = end_token - perspective_segment.end_token
            self.entries = [e.set_end_token(e.end_token + drift) for e in self.entries]

        self._filter_invalid()
        self._reset_cache()
        return self

    def split(self, persp_id, splitidx):  # NB, splitidx inclusive to LEFT
        return self.copy().set(persp_id, end_token=splitidx), self.copy().set(persp_id, start_token=splitidx+1)
    
    def copy(self):
        return MatchAtom(entries=[e.copy() for e in self.entries], description=self.description, cache={k:v for k,v in self.cache.items()})

    def filter_solutions(self, allowed_soln_ids, reset_cache=True):
        return MatchAtom(
            [e.copy() for e in self.entries if e.soln_id in allowed_soln_ids],
            cache=dict() if reset_cache else self.cache.copy()
        )

    @property
    def is_empty(self):
        return len(self.entries) == 0

