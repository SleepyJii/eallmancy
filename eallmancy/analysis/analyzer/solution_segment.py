
import numpy as np
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class SolutionSegment:
    soln_id: int
    soln_length: int   # number of tokens in soln as per JPlag
    start_token: int
    end_token: int     # INCLUSIVE!!!
    start_line: Optional[int] = None  # these need to be optional
    end_line: Optional[int] = None    # because some merge ops require fresh lookup
    original_segid: Optional[int] = None

    def __hash__(self):
        # specifically not including original_segid, because I want to prefer pre-existing None
        return hash(f'{self.soln_id},{self.soln_length},{self.start_token},{self.end_token}')

    def __eq__(self, oth):
        return self.__hash__() == oth.__hash__()
    
    def copy(self):
        return SolutionSegment(
            self.soln_id, self.soln_length,
            self.start_token, self.end_token, start_line=self.start_line, end_line=self.end_line,
            original_segid=self.original_segid
        )
    
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
