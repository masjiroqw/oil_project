
import asyncio
import json
import os
from typing import NamedTuple

import dotenv
from fastapi import HTTPException, UploadFile
from google import genai
from google.genai import types

from logger_config import setup_logger
from src.schemas.schema import FuelReport

logger = setup_logger()
dotenv.load_dotenv()
ALLOWED_TYPES = ["image:jpeg"]

class FuelTuple(NamedTuple):
    total_disiel: float
    total_92: float
    total_95: float
    goal: float
    station_type: str
    
class ApiService:
    def __init__(self, sys_prompt:str) -> None: 
        self.client = genai.Client(api_key=os.environ.get("GOOGLE_API", None))
        self.config = types.GenerateContentConfig(system_instruction=sys_prompt,
                                                  response_schema=FuelReport,
                                                  response_mime_type="application/json")
    """Функция для обработки скриншота с данными"""
    @staticmethod
    async def process_photo(file:UploadFile) -> bytes:
        if file.content_type in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="allowed only jpeg")
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
            except asyncio.TimeoutError as t:
                logger.error(f"Failed to get responce from llm {t}")
                
    """Функция для распаковки ответа ИИ"""            
    async def parse_response(self, response:types.GenerateContentResponse):
        if isinstance(response.parsed, FuelReport):
            report = response.parsed
            goal = report.goal
            station_type = report.station_type
            total_disiel = sum(report.disiel)
            total_92 = sum(report.fuel_92)
            total_95 = report.fuel_95
            return FuelTuple(total_disiel=total_disiel,
                             total_92=total_92,
                             total_95=total_95,
                             goal=goal,
                             station_type=station_type)
        raise TypeError(logger.error("AI return wrong type"))
    
    """Функция для сранвения соотвествия суммы топлива зявленному количеству"""
    async def compare_fuel_data(self, report:FuelTuple) -> dict:
        if report:
            total = sum([report.total_disiel, report.total_92, report.total_95])
            if total == report.goal:
                return {"action": "recording"}
            raise ValueError(logger.error(f"mismatch data, {total} is not equal to {report.goal}"))
    
    """Собранный бизнес сценарий воедино"""
    async def process_api(self, file:UploadFile):
        response = await self.process_llm(file=file)   
        report = await self.parse_response(response=response)     
        action = await self.compare_fuel_data(report=report)    
        """Завтра разобраться с gspread
           Далее должна идти запись в гугл таблицы
           Исходя из того какой тип заправки такую таблицу и открываем
           Также в будущем добавить поле в BaseModel тип отчета, финансовый или обычный"""
           