import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

app = FastAPI()

# 🔑 DeepSeek API 설정 (나중에 Railway 환경변수에서 가져옴)
# 지금 테스트할 때는 아래 "sk-..." 부분에 님의 키를 직접 넣어서 테스트해보셔도 됩니다.
# 하지만 보안을 위해 나중엔 os.environ.get("DEEPSEK_API_KEY")로 바꿔야 합니다.
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "여기에_API_키를_붙여넣어도_됩니다_하지만_비추천")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

class BookRequest(BaseModel):
    url: str

class BookResponse(BaseModel):
    status: str
    message: str
    book_content: str | None = None # 책 내용 (텍스트)

def extract_video_id(url: str):
    """유튜브 URL에서 영상 ID만 쏙 뽑아내는 함수"""
    # 예: https://www.youtube.com/watch?v=dQw4w9WgXcQ -> dQw4w9WgXcQ
    # 예: https://youtu.be/dQw4w9WgXcQ -> dQw4w9WgXcQ
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

@app.get("/")
def read_root():
    return {"status": "Tublisher Server is Running! 🚀"}

@app.post("/api/create_book", response_model=BookResponse)
async def create_book(request: BookRequest):
    print(f"📥 [주문 접수] URL: {request.url}")
    
    video_id = extract_video_id(request.url)
    if not video_id:
        return {"status": "error", "message": "유효하지 않은 유튜브 URL입니다.", "book_content": None}

    try:
        # 1. 유튜브 자막 가져오기 (한국어 우선, 없으면 영어)
        print("1️⃣ 자막 추출 중...")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        
        # 자막 텍스트만 합치기
        full_text = " ".join([entry['text'] for entry in transcript_list])
        print(f"   -> 자막 길이: {len(full_text)}자")

        # 2. DeepSeek에게 책 쓰기 시키기
        print("2️⃣ DeepSeek 집필 시작...")
        
        system_prompt = """
        당신은 베스트셀러 전문 에디터입니다. 
        제공된 유튜브 자막 내용을 바탕으로 가독성 좋은 '전자책 챕터' 하나를 작성하세요.
        
        [지침]
        1. 구어체(말하는 말투)를 완벽한 문어체(책 말투)로 수정하세요.
        2. 서론, 본론(소제목 포함), 결론으로 논리정연하게 구성하세요.
        3. 중요한 개념은 볼드체(**강조**) 처리하세요.
        4. 독자에게 말을 거는 방식이 아니라, 지식을 전달하는 서술형으로 작성하세요.
        """

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"다음 내용을 잘 다듬어진 책 원고로 변환해줘:\n\n{full_text[:15000]}"} 
                # DeepSeek는 입력량이 넉넉하지만, 너무 길면 잘릴 수 있어서 일단 앞부분 1.5만자만 테스트
            ],
            stream=False
        )

        book_content = response.choices[0].message.content
        print("✅ 집필 완료!")

        return {
            "status": "success",
            "message": "책 내용 생성 완료!",
            "book_content": book_content
        }

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return {"status": "error", "message": f"서버 오류: {str(e)}", "book_content": None}