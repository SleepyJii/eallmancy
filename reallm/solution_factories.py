

from typing import Optional
import re




class EvaluationFactory:
    def __init__(self):
        pass


class ArtifactFactory:
    def __init__(self, property_patterns=dict(), evaluation_factory=EvaluationFactory()):
        self._property_patterns = property_patterns
        self._eval_factory = evaluation_factory
    
    def add_property_patterns(self, **kwargs):
        ptn = dict(**self._property_patterns)
        ptn.update(kwargs)
        return ArtifactFactory(property_patterns=ptn, evaluation_factory=self._eval_factory)
    
    def construct_from_response(resp: str):
        pass