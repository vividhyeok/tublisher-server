import os
import re
import tempfile
import requests
import markdown
import glob
import unicodedata  # 한글 자모음 합치기용 (필수)
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from ebooklib import epub
import yt_dlp
import google.generativeai as genai

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Railway 환경변수에서 키 가져오기
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# DeepSeek 클라이언트 설정
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Gemini 설정
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class BookRequest(BaseModel):
    url: str

def get_video_title(url: str):
    """영상 제목 가져오기 + 한글 정규화(NFC)"""
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube Summary')
            # Mac/Linux 서버 환경에서 분리된 한글 자모음을 하나로 합침
            return unicodedata.normalize('NFC', title)
    except:
        return "YouTube Video Summary"

def extract_video_id(url: str):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def download_audio(url: str):
    """
    yt-dlp를 사용하여 오디오 다운로드 및 mp3 변환
    (nixpacks.toml 설정을 통해 ffmpeg가 설치되어 있어야 함)
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        # ffmpeg를 사용하여 mp3로 변환 (용량 절약 및 호환성 확보)
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
        'outtmpl': '/tmp/%(id)s.%(ext)s',  # Railway 임시 폴더 경로
        'quiet': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"/tmp/{info['id']}.mp3"

def create_epub_file(title: str, content_markdown: str, video_id: str):
    """EPUB 생성 + 한글 인코딩 및 폰트 처리"""
    
    # 제목과 본문 모두 자모음 합치기 (NFC 정규화) - 중요!
    title = unicodedata.normalize('NFC', title)
    content_markdown = unicodedata.normalize('NFC', content_markdown)

    book = epub.EpubBook()
    book.set_identifier(video_id)
    book.set_title(title)
    book.set_language('ko')
    book.add_author('Tublisher AI')

    # Markdown을 HTML로 변환
    html_content = markdown.markdown(content_markdown)
    
    c1 = epub.EpubHtml(title='Summary', file_name='chap_01.xhtml', lang='ko')
    
    # 리더기에서 한글이 깨지지 않도록 meta charset과 스타일 설정 추가
    c1.content = f"""
        <?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>{title}</title>
        <style>
            body {{ 
                font-family: sans-serif; 
                line-height: 1.8; 
                color: #333; 
                word-break: keep-all; /* 한글 단어 단위 줄바꿈 */
            }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; margin-top: 30px; border-left: 5px solid #eee; padding-left: 10px; }}
            strong {{ color: #c0392b; background-color: #f9f9f9; padding: 2px 4px; border-radius: 4px; }}
            hr {{ border: 0; border-top: 1px solid #eee; margin: 20px 0; }}
            .metadata {{ color: gray; font-size: 0.8em; margin-top: 50px; text-align: center; border-top: 1px dashed #ccc; padding-top: 10px; }}
        </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div style="color:#7f8c8d; font-style:italic; margin-bottom:20px;">
                이 전자책은 AI가 영상을 분석하여 생성했습니다.
            </div>
            <hr/>
            {html_content}
            <div class="metadata">
                <p>Original Video: https://youtu.be/{video_id}</p>
                <p>Published by Tublisher</p>
            </div>
        </body>
        </html>
    """
    
    book.add_item(c1)
    book.toc = (epub.Link('chap_01.xhtml', 'Summary', 'intro'), (c1, []))
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', c1]

    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
        epub.write_epub(tmp.name, book)
        return tmp.name

def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@app.get("/")
def read_root():
    return {"status": "Tublisher Factory Running! 🏭"}

@app.post("/api/create_book")
async def create_book(request: BookRequest, background_tasks: BackgroundTasks):
    print(f"📥 [주문 접수] URL: {request.url}")
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # 1. 제목 및 메타데이터 추출
    video_title = get_video_title(request.url)
    book_content = ""
    
    # 2. 자막 확인 (1차 시도)
    transcript_text = None
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        print(f"   📜 자막 발견! (DeepSeek 모드)")
    except:
        print("   ⚠️ 자막 없음! (Gemini 오디오 모드)")

    # AI 페르소나 및 지침
    system_prompt = """
    당신은 전문 도서 편집자입니다. 제공된 내용을 바탕으로 가독성 높은 '전자책 챕터'를 작성하세요.
    [지침]
    1. 구어체를 완벽한 문어체로 변환하고, 소제목(Heading 2)을 적극 활용하여 구조화하세요.
    2. 핵심 내용은 볼드체로 강조하고, 마크다운 형식으로 출력하세요.
    3. 요약보다는 내용을 충실히 서술하여 지식을 전달하세요.
    """

    # 3. AI 집필 로직 (분기 처리)
    
    # [CASE A] 자막이 있는 경우 -> DeepSeek 사용
    if transcript_text:
        if not DEEPSEEK_API_KEY:
             book_content = "## 설정 오류\n\nDeepSeek API Key가 설정되지 않았습니다."
        else:
            try:
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"다음 자막을 책으로 변환해줘:\n\n{transcript_text[:15000]}"}
                    ]
                )
                book_content = response.choices[0].message.content
            except Exception as e:
                book_content = f"## AI 오류\n\nDeepSeek 처리 중 오류 발생: {e}"
    
    # [CASE B] 자막이 없는 경우 -> Gemini + ffmpeg 오디오 분석
    else:
        if not GOOGLE_API_KEY:
            book_content = "## 설정 오류\n\n자막이 없는 영상은 Gemini가 필요합니다. Railway 변수에 GOOGLE_API_KEY를 설정해주세요."
        else:
            audio_path = None
            try:
                print("   🎧 오디오 다운로드 중... (ffmpeg 변환)")
                audio_path = download_audio(request.url)
                
                print("   📤 Gemini 분석 중...")
                audio_file = genai.upload_file(audio_path)
                
                print("   🤖 Gemini 집필 중...")
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([
                    system_prompt + "\n이 오디오 파일을 듣고 위 지침에 따라 책 원고를 작성해줘.",
                    audio_file
                ])
                book_content = response.text
                
                # Gemini 쪽 파일 삭제 (청소)
                genai.delete_file(audio_file.name)
            except Exception as e:
                print(f"오디오 처리 에러: {e}")
                book_content = f"## 처리 실패\n\n오디오 분석 중 오류가 발생했습니다.\nError: {e}\n\n(참고: 서버에 ffmpeg가 설치되어 있어야 합니다.)"
            finally:
                # 로컬 오디오 파일 삭제
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)

    # 4. EPUB 생성 및 반환
    print("   📚 제본 및 배송...")
    epub_path = create_epub_file(video_title, book_content, video_id)
    
    # 파일 전송 후 삭제 예약
    background_tasks.add_task(remove_file, epub_path)

    return FileResponse(
        path=epub_path,
        filename=f"summary_{video_id}.epub",
        media_type='application/epub+zip'
    )