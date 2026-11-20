
import asyncio
import os

import dotenv
from fastapi import HTTPException, UploadFile
from google import genai
from google.genai import types

from logger_config import setup_logger
from src.schemas.schema import FuelReport

logger = setup_logger()
dotenv.load_dotenv()
ALLOWED_TYPES = ["image:jpeg"]

class MainService:
    def __init__(self, sys_prompt:str) -> None: 
        self.client = genai.Client(api_key=os.environ.get("GOOGLE_API", None))
        self.config = types.GenerateContentConfig(system_instruction=sys_prompt,
                                                  response_json_schema=FuelReport,
                                                  response_mime_type="application/json")

    async def process_photo(self, file:UploadFile) -> bytes:
        if file.content_type in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="allowed only jpeg")
        content = await file.read()
        return content
    
    async def process_llm(self, file:UploadFile) -> types.GenerationContentResponce:
        bytes = await self.process_photo(file=file)
        if self.client is not None:
            try:
                chat = self.client.aio.chats.create(
                       
                       model="gemini-3.1-flash-lite",
                       config=self.config,
                       )
                responce = await chat.send_message([types.Part.from_bytes(data=bytes, 
                                                                          mime_type="image/jpeg")])
                return responce
            except asyncio.TimeoutError:
                logger.error(msg="Failed to get responce from llm")
                
    