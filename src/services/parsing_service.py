from google.genai import types

from src.schemas.schema import FinancialReport, FinancialTuple, FuelReport, FuelTuple


class ParsingService:
        
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
        raise TypeError("AI return wrong type")
    
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