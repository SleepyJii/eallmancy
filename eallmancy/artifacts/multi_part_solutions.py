from eallmancy.artifacts.artifact import Artifact
from typing import Optional, List
import copy
from dataclasses import dataclass
import re
from typing import List


class MultiPartSolution(Artifact):
    def __init__(self, raw_resp, *args, **kwargs):
        super().__init__(raw_resp, *args, **kwargs)
        self.solution_part_strs = re.findall(r'```[^\n]*\n(.*?)```', raw_resp, re.DOTALL)
    

class DummyMultiPartSolution:
    def __init__(self, solution_part_strs):
        self.solution_part_strs = solution_part_strs


@dataclass
class SearchReplaceBlock:
    search_block: str
    replace_block: str

    def __str__(self):
        return f'<<<<<<<< SEARCH\n{self.search_block}\n========\n{self.replace_block}\n>>>>>>>> REPLACE'

    @staticmethod
    def from_str(rawstr):
        parses = re.findall(r'<<<<<<<< SEARCH\n(.*?)\n========\n(.*?)\n>>>>>>>> REPLACE', rawstr, re.DOTALL)
        return [SearchReplaceBlock(*p) for p in parses]

    def apply_to(self, sourcestr):
        return sourcestr.replace(self.search_block, self.replace_block)
        

class DiffSolution(MultiPartSolution):
    def __init__(self, raw_resp, parent: Optional[MultiPartSolution] = None, *args, **kwargs):
        super(MultiPartSolution, self).__init__(raw_resp, *args, **kwargs)
        self.parent = None
        self.srbs = SearchReplaceBlock.from_str(raw_resp)
        self._solution_part_strs = None

    def set_parent(self, parent: Optional[MultiPartSolution]):
        self.parent = parent
        return self

    @property
    def solution_part_strs(self):
        if self.parent is None:
            raise Exception('cannot consider `solution_part_strs` of DiffSolution without providing its parent MultiPartSolution!')
        if self._solution_part_strs is not None:
            return self._solution_part_strs
        _pts = []
        for s in self.parent.solution_part_strs:
            _s = copy.deepcopy(s)
            for srb in self.srbs:
                _s = srb.apply_to(_s)
            _pts.append(_s)
        self._solution_part_strs = _pts # caching to prevent recalc later on
        return _pts

