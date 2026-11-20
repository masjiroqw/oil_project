from enum import Enum

from pydantic import BaseModel


class StationType(str, Enum):
    NYAGAN =  "nyagan"
    YNYGAN = "ynygan"
    
    
class FuelReport(BaseModel):
    station_type: StationType
    disiel: list[float]
    fuel_92: list[float]
    fuel_95: float
    goal: float