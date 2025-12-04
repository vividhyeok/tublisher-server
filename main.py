from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI()

# 데이터 규격 (안드로이드랑 짝꿍)
class BookRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"status": "Tublisher Server is Running!"}

@app.post("/api/create_book")
async def create_book(request: BookRequest):
    print(f"📥 [Railway] 주문 접수됨: {request.url}")
    
    # TODO: 여기서 나중에 DeepSeek 부르고 EPUB 만드는 로직 들어감
    
    return {
        "status": "success",
        "message": "Railway 서버가 정상적으로 접수했습니다!",
        "jobId": "job_railway_001"
    }