

import dotenv
from fastapi import UploadFile

from logger_config import setup_logger
from src.schemas.schema import (
    Reports,
    ReportType,
)
from src.services.financial_report_service import FinancialReportService
from src.services.fuel_report_service import FuelReportService
from src.services.llm_service import LlmService

logger = setup_logger()
dotenv.load_dotenv()


     
class ApiService:
    def __init__(self) -> None:
        self.llm_service = LlmService()
        self.fuel_service = FuelReportService()
        self.financial_service = FinancialReportService()
    
    async def initial_parsing(self, file:UploadFile):
        bytes = await self.llm_service.process_photo(file=file)
        response = await self.llm_service.process_llm(config=self.llm_service.initial_config, bytes=bytes)
        if isinstance(response.parsed, ReportType):
            report = response.parsed
            if report.report_type == Reports.FUEL_REPORT:
                await self.fuel_service.process_fuel_report(bytes=bytes)
            if report.report_type == Reports.FINANCIAL_REPORT:
                await self.financial_service.process_financial_report(bytes=bytes)
            
        
  
                

        
