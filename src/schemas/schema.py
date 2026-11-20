from pydantic import BaseModel


class FuelReport(BaseModel):
    disiel: list[float]
    fuel_92: list[float]
    fuel_95: float
    