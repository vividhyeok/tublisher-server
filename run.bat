@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creating local virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [error] Python virtual environment creation failed.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

python -c "import PySide6, openai, yt_dlp, ebooklib, markdown, youtube_transcript_api" >nul 2>nul
if errorlevel 1 (
  echo [setup] Installing Python dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [error] Dependency installation failed.
    pause
    exit /b 1
  )
)

if "%OPENAI_API_KEY%"=="" (
  echo [warn] OPENAI_API_KEY is not set. OpenAI planning/writing/STT will fail until it is configured.
)

python main.py

if errorlevel 1 (
  echo [error] Application exited with an error.
  pause
  exit /b 1
)

endlocal
