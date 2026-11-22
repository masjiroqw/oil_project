
from fastapi import FastAPI, UploadFile

from prompts import FINANCIAL_PROMPT, FUEL_PROMPT, INITIAL_PROMPT
from src.services.api_service import ApiService

app = FastAPI()





@app.post("/upload")
async def get_photo(file:UploadFile):
    service = ApiService(fuel_sys_prompt=FUEL_PROMPT, 
                         financial_sys_prompt=FINANCIAL_PROMPT,
                         initial_sys_prompt=INITIAL_PROMPT)
    await service.initial_parsing(file=file)