
import asyncio
import math
import os
from typing import NamedTuple

import dotenv
import gspread
from fastapi import HTTPException, UploadFile
from google import genai
from google.genai import types

from logger_config import setup_logger
from src.schemas.schema import FuelReport, StationType

logger = setup_logger()
dotenv.load_dotenv()
ALLOWED_TYPES = ["image/jpeg", "image/png"]

class FuelTuple(NamedTuple):
    total_diesel: float
    total_92: float
    total_95: float
    goal: float
    station_type: str
    
class ApiService:
    def __init__(self, sys_prompt:str) -> None: 
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API", None))
        self.config = types.GenerateContentConfig(system_instruction=sys_prompt,
                                                  response_schema=FuelReport,
                                                  response_mime_type="application/json")
    """Функция для обработки скриншота с данными"""
    @staticmethod
    async def process_photo(file:UploadFile) -> bytes:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Allowed only jpeg")
        content = await file.read()
        return content
    
    """Функция для взимания данных с фото"""
    async def process_llm(self, file:UploadFile) -> types.GenerateContentResponse|None:
        bytes = await self.process_photo(file=file)
        if self.client is not None:
            try:
                chat = self.client.aio.chats.create(
                       
                       model="gemini-3.1-flash-lite",
                       config=self.config,
                       )
                response = await chat.send_message([types.Part.from_bytes(data=bytes, 
                                                                          mime_type="image/jpeg")])
                return response
            except TimeoutError as t:
                logger.error(f"Failed to get responce from llm {t}")
                
    """Функция для распаковки ответа ИИ"""            
    async def parse_response(self, response:types.GenerateContentResponse) -> FuelTuple:
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
            
            
    
    """Функция для сранвения соотвествия суммы топлива зявленному количеству"""
    async def compare_fuel_data(self, report:FuelTuple) -> dict:
        if report:
            total = sum([report.total_diesel, report.total_92, report.total_95])
            if math.isclose(total, report.goal, abs_tol=0.01):
                return {"action": "recording"}
            raise ValueError(f"Mismatch data, {total} is not equal to {report.goal}")
    
    """Собранный бизнес сценарий воедино"""
    async def process_api(self, file:UploadFile) -> None:
        sheets_serivce = SheetsService()
        response = await self.process_llm(file=file)   
        report = await self.parse_response(response=response)     
        action = await self.compare_fuel_data(report=report)    
        if action.get("action", None) == "recording":
            await sheets_serivce.save_report(report=report)
            logger.info("Successful recording")
   
class SheetsService:
    """Запись отчётов в Google таблицу"""

    # Тип заправки -> название листа (должно точно совпадать с названием вкладки)
    SHEETS = {
        StationType.NYAGAN: "Остаток Нягань",
        StationType.YNYGAN: "Остаток Уньюган",
    }

    def __init__(self) -> None:
        gc = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS"])
        self.spreadsheet = gc.open_by_key(os.environ["SHEET_ID"])

    DT_COLUMN = 5                  # колонка E (ДТ) — по ней ищем первую пустую строку
    DATA_RANGE = "E{row}:H{row}"   # E — ДТ, F — АИ-92, G — АИ-95, H — goal

    def _write(self, report: FuelTuple) -> int:
        ws = self.spreadsheet.worksheet(self.SHEETS[StationType(report.station_type)])

        # col_values возвращает значения колонки E до последней заполненной ячейки,
        # значит следующая строка после них — первая пустая
        row = len(ws.col_values(self.DT_COLUMN)) + 1

        ws.update(
            [[report.total_diesel, report.total_92, report.total_95, report.goal]],
            self.DATA_RANGE.format(row=row),
            value_input_option="USER_ENTERED",  # чтобы числа легли как числа, а не текст
        )
        return row

    async def save_report(self, report: FuelTuple) -> None:
        # gspread синхронный, поэтому запускаем в отдельном потоке
        row = await asyncio.to_thread(self._write, report)
        logger.info(f"Report saved to sheet '{self.SHEETS[StationType(report.station_type)]}', row {row}")
