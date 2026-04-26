from __future__ import annotations

import shutil
from pathlib import Path

from app.core.errors import FfmpegNotFoundError


def resolve_ffmpeg_dir(ffmpeg_path: str | None = None) -> Path:
    if ffmpeg_path:
        candidate = Path(ffmpeg_path)
        if candidate.is_file():
            return candidate.parent
        if candidate.is_dir() and (candidate / _exe_name("ffmpeg")).exists():
            return candidate

    found = shutil.which("ffmpeg")
    if found:
        return Path(found).parent

    raise FfmpegNotFoundError()


def _exe_name(name: str) -> str:
    return f"{name}.exe" if shutil.which("where") else name

