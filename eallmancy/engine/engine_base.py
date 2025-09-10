

class EngineBase:
    def __init__(self, api_spec=None, problem_spec: ProblemSpec=None, tracing=True, debug=False, **kwargs):
        pass

    def add_hook(self, hook_func):
        pass

    def is_ready(self):
        return self._sampler is not None and self._problem_spec is not None

    def start(self):
        pass
    
    def finish(self):
        pass

    def start_trace(self):
        pass
    
    def dump_trace(self):
        pass
    
    def register_artifact(self, arte: Artifact, parents: List[Artifact] = [], disable_hooks=False, **tags):
        pass
        
    async def async_register_artifact(self, arte: Artifact, parents: List[Artifact] = [], disable_hooks=False, **tags):
        pass

    def build_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):
        pass


    def generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):
        pass
    
    async def async_build_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):
        pass

    async def async_generate_artifact(self, prompt: str, arte_class, parents: List[Artifact] = [], register=True):
        pass