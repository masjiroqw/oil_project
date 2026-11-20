
from fastapi import FastAPI, HTTPException, UploadFile

app = FastAPI()



@app.post("/upload")
async def get_photo(file:UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="allowed only jpeg")
    content = await file.read()
    return content