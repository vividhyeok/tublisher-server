from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.models import Transcript


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio_path: Path, language: str) -> Transcript:
        ...

