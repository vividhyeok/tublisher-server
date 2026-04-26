from __future__ import annotations

import os
import unicodedata
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.errors import SpeechToTextError
from app.core.models import Transcript, TranscriptSegment


class OpenAISpeechToTextProvider:
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_sec: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_STT_MODEL") or model or "gpt-4o-transcribe"
        self.timeout_sec = timeout_sec
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def transcribe(self, audio_path: Path, language: str) -> Transcript:
        if not self.client:
            raise SpeechToTextError("OPENAI_API_KEY가 설정되지 않았습니다.")
        if not audio_path.exists():
            raise SpeechToTextError(f"오디오 파일을 찾지 못했습니다: {audio_path.name}")

        try:
            with audio_path.open("rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    response_format="json",
                    timeout=self.timeout_sec,
                )
        except Exception as exc:
            raise SpeechToTextError(str(exc)) from exc

        text = _extract_text(response)
        if not text.strip():
            raise SpeechToTextError("OpenAI STT가 빈 전사 결과를 반환했습니다.")

        normalized = unicodedata.normalize("NFC", text)
        return Transcript(
            source="audio_stt",
            language=language,
            segments=[TranscriptSegment(start=0, end=0, text=normalized)],
            raw_text=normalized,
        )


def _extract_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if text:
        return str(text)
    if isinstance(response, dict):
        return str(response.get("text", ""))
    return str(response)
