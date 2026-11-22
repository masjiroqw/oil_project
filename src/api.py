


from fastapi import FastAPI, UploadFile

from src.services.api_service import ApiService

app = FastAPI()





@app.post("/upload")
async def get_photo(file:UploadFile):
    api_service = ApiService()
    await api_service.initial_parsing(file=file)