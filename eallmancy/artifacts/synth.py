from pathlib import Path
import os
import glob
import re

from eallmancy.artifacts.artifact import Artifact



class SynthArtifact(Artifact):
    def __init__(self, sstr, source):
        self.content = sstr
        self.source = source
        self.is_solution = False
        self.trace_id = None


class SynthSolution(SynthArtifact):
    def __init__(self, sstr, source: str):
        super().__init__(sstr, source)
        self.is_solution = True
        self._fitness = float('nan')

    @property
    def fitness(self):
        return self._fitness

    def __str__(self):
        return f"[{self.source}]\n{self.content}"

    
class SynthSTReflection(SynthArtifact):
    def __init__(self, sstr, source: str):
        super().__init__(sstr, source)
        
    def __str__(self):
        return f"[{self.source}]\n{self.content}"
        
class SynthLTReflection(SynthSTReflection):
    pass


