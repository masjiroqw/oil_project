from enum import Enum
from typing import NamedTuple

from pydantic import BaseModel


class Reports(str, Enum):
    FINANCIAL_REPORT = "financial_report"
    FUEL_REPORT = "fuel_report"

class StationType(str, Enum):
    NYAGAN =  "nyagan"
    YNYGAN = "ynygan"



class FuelTuple(NamedTuple):
    total_diesel: float
    total_92: float
    total_95: float
    goal: float
    station_type: str
    
class FinancialTuple(NamedTuple):
    cash: float
    card:float
    submitted:float
    station_type: str 
       
    
class FuelReport(BaseModel):
    station_type: StationType
    diesel: list[float]
    fuel_92: list[float]
    fuel_95: list[float]
    goal: float

class ReportType(BaseModel):
    report_type: Reports
  
class FinancialReport(BaseModel):
    station_type: StationType
    cash: float
    card: float
    submitted: float