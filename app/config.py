from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


@dataclass(frozen=True)
class AppConfig:
    output_dir: Path
    theme: str = "system"
    prefer_subtitles: bool = True
    allow_audio_fallback: bool = True
    yt_dlp_path: str = ""
    ffmpeg_path: str = "bin/ffmpeg.exe"
    ffprobe_path: str = "bin/ffprobe.exe"
    default_planning_provider: str = "openai"
    default_writing_provider: str = "openai"
    default_stt_provider: str = "openai"
    openai_stt_model: str = "gpt-4o-transcribe"
    timeout_sec: int = 120
    max_retries: int = 2
    default_language: str = "ko"
    include_source_url: bool = True
    default_mode: str = "balanced"


def default_config() -> AppConfig:
    return AppConfig(output_dir=Path.home() / "Documents" / "YouTubeEPUB")


def load_config(path: Path | None = None) -> AppConfig:
    load_dotenv()
    if path is None:
        path = Path("config.toml")
    if not path.exists() or tomllib is None:
        return default_config()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return _config_from_dict(data)


def _config_from_dict(data: dict[str, Any]) -> AppConfig:
    defaults = default_config()
    app = data.get("app", {})
    youtube = data.get("youtube", {})
    ffmpeg = data.get("ffmpeg", {})
    llm = data.get("llm", {})
    epub = data.get("epub", {})
    return AppConfig(
        output_dir=Path(app.get("output_dir") or defaults.output_dir),
        theme=str(app.get("theme", defaults.theme)),
        prefer_subtitles=bool(youtube.get("prefer_subtitles", defaults.prefer_subtitles)),
        allow_audio_fallback=bool(youtube.get("allow_audio_fallback", defaults.allow_audio_fallback)),
        yt_dlp_path=str(youtube.get("yt_dlp_path", defaults.yt_dlp_path)),
        ffmpeg_path=str(ffmpeg.get("ffmpeg_path", defaults.ffmpeg_path)),
        ffprobe_path=str(ffmpeg.get("ffprobe_path", defaults.ffprobe_path)),
        default_planning_provider=str(llm.get("default_planning_provider", defaults.default_planning_provider)),
        default_writing_provider=str(llm.get("default_writing_provider", defaults.default_writing_provider)),
        default_stt_provider=str(llm.get("default_stt_provider", defaults.default_stt_provider)),
        openai_stt_model=str(llm.get("openai_stt_model", defaults.openai_stt_model)),
        timeout_sec=int(llm.get("timeout_sec", defaults.timeout_sec)),
        max_retries=int(llm.get("max_retries", defaults.max_retries)),
        default_language=str(epub.get("default_language", defaults.default_language)),
        include_source_url=bool(epub.get("include_source_url", defaults.include_source_url)),
        default_mode=str(epub.get("default_mode", defaults.default_mode)),
    )
