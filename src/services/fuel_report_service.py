import math

from google.genai import types

from logger_config import setup_logger
from src.schemas.schema import FuelReport, FuelTuple
from src.services.google_sheets_service import SheetsService
from src.services.llm_service import LlmService

logger = setup_logger()

class FuelReportService:
    def __init__(self) -> None:
        self.llm_service = LlmService()
    
    """Функция для распаковки ответа ИИ"""            
    async def parse_fuel_response(self, response:types.GenerateContentResponse) -> FuelTuple:
        if isinstance(response.parsed, FuelReport):
            report = response.parsed
            goal = report.goal
            station_type = report.station_type
            total_diesel = sum(report.diesel)
            total_92 = sum(report.fuel_92)
            total_95 = sum(report.fuel_95)
            return FuelTuple(total_diesel=total_diesel,
                                total_92=total_92,
                                total_95=total_95,
                                goal=goal,
                                station_type=station_type)   
      
    """Функция для сранвения соотвествия суммы топлива зявленному количеству"""
    async def compare_fuel_data(self, report:FuelTuple) -> dict:
        if report:
            total = sum([report.total_diesel, report.total_92, report.total_95])
            if math.isclose(total, report.goal, abs_tol=0.01):
                return {"action": "recording"}
            raise ValueError(f"Mismatch data, {total} is not equal to {report.goal}")
          
    """Собранный бизнес сценарий воедино"""
    async def process_fuel_report(self, bytes:bytes) -> None:
        sheets_serivce = SheetsService()
        response = await self.llm_service.process_llm(config=self.llm_service.fuel_config, bytes=bytes)   
        report = await self.parse_fuel_response(response=response)     
        action = await self.compare_fuel_data(report=report)    
        if action.get("action", None) == "recording":
            await sheets_serivce.save_fuel_report(report=report)
            logger.info("Successful recording")    