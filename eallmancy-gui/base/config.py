
from pydantic import BaseModel


class Config(BaseModel):
    repoPath: str
    evalScript: str
    description: str
    algorithm: str
    overwrite: bool
    