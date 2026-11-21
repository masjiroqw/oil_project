
from fastapi import FastAPI, HTTPException, UploadFile

from prompts import GEMINI_PROMPT
from src.services.api_service import ApiService

app = FastAPI()



@app.post("/upload")
async def get_photo(file:UploadFile):
    service = ApiService(sys_prompt=GEMINI_PROMPT)
    await service.process_api(file=file)