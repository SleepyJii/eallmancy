
from typing import List, Optional, Dict
import pickle as pk

from eallmancy.analysis.analyzer.pairwise_trace_analysis import PairwiseTraceAnalysis
from eallmancy.analysis.analyzer.segment_trace_analysis import SegmentTraceAnalysis


class AnalysisCache:
    
    def __init__(self):
        self.pairwise = None
        self.segment = None

    @property
    def empty(self):
        return (self.pairwise is None) and (self.segment is None)

    def load(self, pth: str, name: List[str]=None):
        if name.lower() == 'pairwise':
            with open(pth, 'rb') as f:
                self.pairwise = pk.load(f)
        elif name.lower() == 'segment':
            with open(pth, 'rb') as f:
                self.segment = pk.load(f)
        elif name is None:
            if type(obj) is AnalysisCache:
                self.pairwise = obj.pairwise
                self.segment = obj.segment
            else:
                raise Exception(f'could not load type `{type(obj)}` into AnalysisCache')
        else:
            raise Exception(f'unknown analysis type name `{name}`')
        return self
    
    def is_loaded(self, name: str):
        return hasattr(self, name) and getattr(self, name) is not None
