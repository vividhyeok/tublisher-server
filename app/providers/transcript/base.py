from __future__ import annotations

from typing import Protocol

from app.core.models import Transcript, VideoMeta


class TranscriptProvider(Protocol):
    def get_metadata(self, youtube_url: str) -> VideoMeta:
        ...

    def get_transcript(self, youtube_url: str, language: str) -> Transcript:
        ...

