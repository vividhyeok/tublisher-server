from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AudioFallbackProvider(Protocol):
    def download_audio(self, youtube_url: str, output_dir: Path) -> Path:
        ...

