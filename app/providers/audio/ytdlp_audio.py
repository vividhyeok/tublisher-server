from __future__ import annotations

from pathlib import Path

import yt_dlp

from app.core.errors import AudioDownloadError
from app.providers.audio.ffmpeg_utils import resolve_ffmpeg_dir


class YtDlpAudioFallbackProvider:
    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path

    def download_audio(self, youtube_url: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg_dir = resolve_ffmpeg_dir(self.ffmpeg_path)
        opts = {
            "format": "bestaudio/best",
            "ffmpeg_location": str(ffmpeg_dir),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }
            ],
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
        except Exception as exc:
            raise AudioDownloadError(str(exc)) from exc

        audio_path = output_dir / f"{info['id']}.mp3"
        if not audio_path.exists():
            raise AudioDownloadError("yt-dlp completed but mp3 file was not found.")
        return audio_path

