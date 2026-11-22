from google.genai import types

from src.schemas.schema import FinancialReport, FinancialTuple
from src.services.google_sheets_service import SheetsService
from src.services.llm_service import LlmService


class FinancialReportService:
    def __init__(self) -> None:
        self.llm_service = LlmService()
        
    async def parse_financial_response(self, response:types.GenerateContentResponse) -> FinancialTuple:
        if isinstance(response.parsed, FinancialReport):
            report = response.parsed
            cash = report.cash
            card = report.card
            submitted = report.submitted
            station_type = report.station_type
            return FinancialTuple(cash=cash, 
                                  card=card, 
                                  station_type=station_type, 
                                  submitted=submitted)
        raise TypeError("AI return wrong type")        
            
  
    
    
            
    async def process_financial_report(self, bytes:bytes):
        sheets_service = SheetsService()
        response = await self.llm_service.process_llm(config=self.llm_service.financial_config, bytes=bytes)
        report = await self.parse_financial_response(response=response)
        await sheets_service.save_financial_report(report=report)