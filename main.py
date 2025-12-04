import os
import re
import tempfile
import requests
import markdown
import glob
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from ebooklib import epub
import yt_dlp
import google.generativeai as genai

app = FastAPI()

# 🔑 API 키 설정 (Railway Variables에서 설정 필요)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# 1. DeepSeek 클라이언트 (자막 있을 때용 - 가성비 & 속도)
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# 2. Gemini 클라이언트 (자막 없을 때용 - 듣기 & 보기 능력자)
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class BookRequest(BaseModel):
    url: str

def get_video_title(url: str):
    """영상 제목 가져오기 (yt-dlp 사용이 더 정확함)"""
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'YouTube Summary')
    except:
        return "YouTube Video Summary"

def extract_video_id(url: str):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def download_audio(url: str):
    """유튜브에서 오디오만 가장 낮은 용량으로 빠르게 다운로드"""
    # Railway 같은 클라우드 환경의 임시 폴더(/tmp) 사용
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
        'outtmpl': '/tmp/%(id)s.%(ext)s', 
        'quiet': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"/tmp/{info['id']}.mp3"

def create_epub_file(title: str, content_markdown: str, video_id: str):
    """AI가 작성한 마크다운을 EPUB 파일로 변환"""
    book = epub.EpubBook()
    book.set_identifier(video_id)
    book.set_title(title)
    book.set_language('ko')
    book.add_author('Tublisher AI')

    # Markdown을 HTML로 변환
    html_content = markdown.markdown(content_markdown)
    
    c1 = epub.EpubHtml(title='Summary', file_name='chap_01.xhtml', lang='ko')
    c1.content = f"""
        <html>
        <head>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; color: #333; }}
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

@app.get("/")
def read_root():
    return {"status": "Tublisher Hybrid Server Running! 🚀"}

@app.post("/api/create_book")
async def create_book(request: BookRequest):
    print(f"📥 [주문 접수] URL: {request.url}")
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # 1. 제목 추출
    print("   🎬 메타데이터 분석 중...")
    video_title = get_video_title(request.url)
    book_content = ""
    
    # 2. 자막 추출 시도 (1차 시도)
    transcript_text = None
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        print(f"   📜 자막 발견! (DeepSeek 모드 가동)")
    except:
        print("   ⚠️ 자막 없음! (Gemini 모드 가동)")

    # 3. AI 집필 (분기 처리)
    system_prompt = """
    당신은 전문 도서 편집자입니다. 제공된 내용을 바탕으로 가독성 높은 '전자책 챕터'를 작성하세요.
    [지침]
    1. 구어체를 문어체로 변환하고, 소제목(Heading 2)을 적극 활용하여 구조화하세요.
    2. 핵심 내용은 볼드체로 강조하고, 마크다운 형식으로 출력하세요.
    3. 요약보다는 내용을 충실히 서술하여 지식을 전달하세요.
    """

    # [CASE A] 자막이 있는 경우 -> DeepSeek (빠르고 저렴)
    if transcript_text:
        if not DEEPSEEK_API_KEY:
             book_content = "## 설정 오류\n\nDeepSeek API Key가 없습니다."
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

    # [CASE B] 자막이 없는 경우 -> Gemini 1.5 Flash (오디오 듣기 + 쓰기)
    else:
        if not GOOGLE_API_KEY:
            book_content = "## 설정 오류\n\n자막이 없는 영상은 Gemini가 필요합니다. Railway에 GOOGLE_API_KEY를 설정해주세요."
        else:
            audio_path = None
            try:
                print("   🎧 오디오 다운로드 중... (서버 공간 절약을 위해 저음질)")
                audio_path = download_audio(request.url)
                
                print("   📤 Gemini에게 듣게 하는 중...")
                audio_file = genai.upload_file(audio_path)
                
                print("   🤖 Gemini가 집필 중...")
                # Gemini 1.5 Flash는 오디오 이해 능력이 뛰어납니다.
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([
                    system_prompt + "\n이 오디오 파일을 듣고 위 지침에 따라 책 원고를 작성해줘.",
                    audio_file
                ])
                book_content = response.text
                
                # 처리 후 파일 삭제 (청소)
                genai.delete_file(audio_file.name)
            except Exception as e:
                book_content = f"## 처리 실패\n\n오디오 분석 중 오류가 발생했습니다.\nError: {e}"
            finally:
                # 로컬 오디오 파일 삭제
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)

    # 4. EPUB 생성 및 반환
    print("   📚 제본 및 배송...")
    epub_path = create_epub_file(video_title, book_content, video_id)
    
    return FileResponse(
        path=epub_path,
        filename=f"summary_{video_id}.epub",
        media_type='application/epub+zip'
    )