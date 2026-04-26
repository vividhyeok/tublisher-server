from __future__ import annotations

from app.config import AppConfig
from app.providers.audio.ytdlp_audio import YtDlpAudioFallbackProvider
from app.providers.planning.mock_planner import MockPlanningProvider
from app.providers.planning.openai_planner import OpenAIPlanningProvider
from app.providers.transcript.mock_provider import MockTranscriptProvider
from app.providers.transcript.ytdlp_provider import YoutubeTranscriptProvider
from app.providers.writing.mock_writer import MockWritingProvider
from app.providers.writing.openai_writer import OpenAIWritingProvider
from app.providers.stt.openai_stt import OpenAISpeechToTextProvider


PROVIDER_NAMES = ("openai", "mock")


def create_transcript_provider(config: AppConfig, provider_name: str = "youtube"):
    if provider_name == "mock":
        return MockTranscriptProvider()
    return YoutubeTranscriptProvider(yt_dlp_path=config.yt_dlp_path or None)


def create_audio_provider(config: AppConfig):
    return YtDlpAudioFallbackProvider(ffmpeg_path=config.ffmpeg_path or None)


def create_stt_provider(provider_name: str, config: AppConfig):
    if provider_name == "openai":
        return OpenAISpeechToTextProvider(model=config.openai_stt_model, timeout_sec=config.timeout_sec)
    return None


def create_planning_provider(provider_name: str):
    if provider_name == "openai":
        return OpenAIPlanningProvider()
    return MockPlanningProvider()


def create_writing_provider(provider_name: str):
    if provider_name == "openai":
        return OpenAIWritingProvider()
    return MockWritingProvider()
