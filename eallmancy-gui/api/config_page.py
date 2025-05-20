# api/routes.py
from fastapi import APIRouter, Path, Body, HTTPException
from pydantic import BaseModel
from pathlib import Path


router = APIRouter()

_ALGOS = ["EOH_git"]

@router.get("/api/config/algorithms")
def get_algorithms():
    return _ALGOS


class ValidationRequest(BaseModel):
    value: str

@router.post("/api/config/validate/{field}")
def validate_field(field: str, data: ValidationRequest):
    
    val = data.value.strip()
    
    if field in ["repoPath", "evalScript"]:
        if not Path(val).exists():
            return {"valid": False, "error": "file does not exist"}

    return {"valid": True}
    

class Config(BaseModel):
    repoPath: str
    evalScript: str
    description: str
    algorithm: str
    overwrite: bool

@router.post("/api/config/submit")
def submit_config(config: Config):
    errors = {}

    # verify repo and evalscript paths are valid
    if config.repoPath.strip() == '' or not Path(config.repoPath.strip()).exists():
        errors["repoPath"] = f"`{config.repoPath}` is not a valid directory"
    if config.evalScript.strip() == '' or not Path(config.evalScript.strip()).is_file():
        errors["evalScript"] = f"`{config.evalScript}` is not a valid file"

    # make sure description is not actually empty
    if len(config.description.strip()) == 0:
        errors["description"] = "No description provided"

    # make sure algo is populated
    if config.algorithm not in _ALGOS:
        errors["algorithm"] = f"Unknown algorithm {config.algorithm}"
    
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    return {"status": "success"}

