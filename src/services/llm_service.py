import os

from fastapi import HTTPException, UploadFile
from google import genai
from google.genai import types

from logger_config import setup_logger
from prompts import FINANCIAL_PROMPT, FUEL_PROMPT, INITIAL_PROMPT
from src.schemas.schema import FinancialReport, FuelReport, ReportType

logger = setup_logger()

ALLOWED_TYPES = ["image/jpeg", "image/png"]

class LlmService:
    def __init__(self) -> None: 
            self.client = genai.Client(api_key=os.environ.get("GEMINI_API", None))
            self.fuel_config = types.GenerateContentConfig(system_instruction=FUEL_PROMPT,
                                                      response_schema=FuelReport,
                                                      response_mime_type="application/json")
            self.financial_config = types.GenerateContentConfig(system_instruction=FINANCIAL_PROMPT,
                                                      response_schema=FinancialReport,
                                                      response_mime_type="application/json")
            self.initial_config = types.GenerateContentConfig(system_instruction=INITIAL_PROMPT,
                                                              response_schema=ReportType,
                                                              response_mime_type="application/json")
    """Функция для взимания данных с фото"""
    async def process_llm(self, config:types.GenerateContentConfig, bytes:bytes) -> types.GenerateContentResponse|None:
        if self.client is not None:
            try:
                chat = self.client.aio.chats.create(
                       
                       model="gemini-3.1-flash-lite",
                       config=config,
                       )
                # PNG всегда начинается с этих байтов, всё остальное у нас — JPEG
                mime_type = "image/png" if bytes.startswith(b"\x89PNG") else "image/jpeg"
                response = await chat.send_message([types.Part.from_bytes(data=bytes,
                                                                          mime_type=mime_type)])
                return response
            except TimeoutError as t:
                logger.error(f"Failed to get responce from llm {t}")
    """Функция для обработки скриншота с данными"""
    @staticmethod
    async def process_photo(file:UploadFile) -> bytes:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Allowed only jpeg or png")
        content = await file.read()
        return content