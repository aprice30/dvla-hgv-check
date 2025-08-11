from pydantic import BaseModel
from typing import List, Optional

class Box(BaseModel):
    xmax: int
    xmin: int
    ymax: int
    ymin: int

class Candidate(BaseModel):
    plate: str
    score: float

class Color(BaseModel):
    color: str
    score: float

class ModelMake(BaseModel):
    make: str
    model: str
    score: float

class Orientation(BaseModel):
    orientation: str
    score: float

class Region(BaseModel):
    code: str
    score: float

class Vehicle(BaseModel):
    box: Box
    score: float
    type: str

class Result(BaseModel):
    box: Box
    candidates: List[Candidate]
    color: List[Color]
    direction: int
    dscore: float
    model_make: List[ModelMake]
    orientation: List[Orientation]
    plate: str
    position_sec: float
    region: Region
    score: float
    source_url: str
    vehicle: Vehicle

    class Config:
        protected_namespaces = ()

class Data(BaseModel):
    camera_id: str
    filename: str
    timestamp: str
    timestamp_local: str
    results: List[Result]

class Hook(BaseModel):
    event: str
    filename: str
    id: str
    target: str

class Root(BaseModel):
    data: Data
    hook: Hook