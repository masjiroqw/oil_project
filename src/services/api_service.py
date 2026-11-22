
import asyncio
import math
import os
from re import S
from typing import NamedTuple

import dotenv
import gspread
from fastapi import HTTPException, UploadFile
from google import genai
from google.genai import types

from logger_config import setup_logger
from src.schemas.schema import (
    FinancialReport,
    FuelReport,
    Reports,
    ReportType,
    StationType,
)

logger = setup_logger()
dotenv.load_dotenv()
ALLOWED_TYPES = ["image/jpeg", "image/png"]

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
class ApiService:
    def __init__(self, fuel_sys_prompt:str,financial_sys_prompt, initial_sys_prompt:str) -> None: 
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API", None))
        self.main_config = types.GenerateContentConfig(system_instruction=fuel_sys_prompt,
                                                  response_schema=FuelReport,
                                                  response_mime_type="application/json")
        self.financial_config = types.GenerateContentConfig(system_instruction=financial_sys_prompt,
                                                  response_schema=FinancialReport,
                                                  response_mime_type="application/json")
        self.initial_config = types.GenerateContentConfig(system_instruction=initial_sys_prompt,
                                                          response_schema=ReportType,
                                                          response_mime_type="application/json")
    """Функция для обработки скриншота с данными"""
    @staticmethod
    async def process_photo(file:UploadFile) -> bytes:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Allowed only jpeg")
        content = await file.read()
        return content
    
    async def initial_parsing(self, file:UploadFile):
        bytes = await self.process_photo(file=file)
        response = await self.process_llm(config=self.initial_config, bytes=bytes)
        if isinstance(response.parsed, ReportType):
            report = response.parsed
            if report.report_type == Reports.FUEL_REPORT:
                await self.process_fuel_report(bytes=bytes)
            if report.report_type == Reports.FINANCIAL_REPORT:
                await self.process_financial_report(bytes=bytes)
            
        
    """Функция для взимания данных с фото"""
    async def process_llm(self, config:types.GenerateContentConfig, bytes:bytes) -> types.GenerateContentResponse|None:
        if self.client is not None:
            try:
                chat = self.client.aio.chats.create(
                       
                       model="gemini-3.1-flash-lite",
                       config=config,
                       )
                response = await chat.send_message([types.Part.from_bytes(data=bytes, 
                                                                          mime_type="image/jpeg")])
                return response
            except TimeoutError as t:
                logger.error(f"Failed to get responce from llm {t}")
                
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
        response = await self.process_llm(config=self.main_config, bytes=bytes)   
        report = await self.parse_fuel_response(response=response)     
        action = await self.compare_fuel_data(report=report)    
        if action.get("action", None) == "recording":
            await sheets_serivce.save_fuel_report(report=report)
            logger.info("Successful recording")
            
    async def process_financial_report(self, bytes:bytes):
        sheets_service = SheetsService()
        response = await self.process_llm(config=self.financial_config, bytes=bytes)
        report = await self.parse_financial_response(response=response)
        await sheets_service.save_financial_report(report=report)
        
class SheetsService:
    """Запись отчётов в Google таблицу"""

    # Тип заправки -> название листа (должно точно совпадать с названием вкладки)
    FUEL_SHEETS = {
        StationType.NYAGAN: "Остаток Нягань",
        StationType.YNYGAN: "Остаток Уньюган",
    }
    FINANCIAL_SHEETS = {
        StationType.NYAGAN: "Закуп,реализация Нягань",
        StationType.YNYGAN: "Закуп, реализация Уньюган",
    }

    # Топливный отчёт: колонка E (ДТ) — по ней ищем первую пустую строку
    FUEL_COLUMN = 5
    FUEL_RANGE = "E{row}:H{row}"        # E — ДТ, F — АИ-92, G — АИ-95, H — goal

    # Финансовый отчёт: колонка D (Реализация наличные) — по ней ищем первую пустую строку
    FINANCIAL_COLUMN = 4
    FINANCIAL_RANGE = "D{row}:F{row}"   # D — реализация наличные, E — реализация безнал, F — сдано

    def __init__(self) -> None:
        gc = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS"])
        self.spreadsheet = gc.open_by_key(os.environ["SHEET_ID"])

    def _append(self, sheet_name: str, column: int, range_template: str, values: list) -> int:
        """Пишет values в первую пустую строку листа (пустую по колонке column)."""
        ws = self.spreadsheet.worksheet(sheet_name)

        # col_values возвращает значения колонки до последней заполненной ячейки,
        # значит следующая строка после них — первая пустая
        row = len(ws.col_values(column)) + 1

        ws.update(
            [values],
            range_template.format(row=row),
            value_input_option="USER_ENTERED",  # чтобы числа легли как числа, а не текст
        )
        return row

    async def save_fuel_report(self, report: FuelTuple) -> None:
        sheet = self.FUEL_SHEETS[StationType(report.station_type)]
        values = [report.total_diesel, report.total_92, report.total_95, report.goal]
        # gspread синхронный, поэтому запускаем в отдельном потоке
        row = await asyncio.to_thread(self._append, sheet, self.FUEL_COLUMN, self.FUEL_RANGE, values)
        logger.info(f"Fuel report saved to sheet '{sheet}', row {row}")

    async def save_financial_report(self, report: FinancialTuple) -> None:
        sheet = self.FINANCIAL_SHEETS[StationType(report.station_type)]
        values = [report.cash, report.card, report.submitted]
        row = await asyncio.to_thread(self._append, sheet, self.FINANCIAL_COLUMN, self.FINANCIAL_RANGE, values)
        logger.info(f"Financial report saved to sheet '{sheet}', row {row}")
