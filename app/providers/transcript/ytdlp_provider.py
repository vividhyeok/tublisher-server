from __future__ import annotations

import re
import unicodedata
from typing import Any

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.errors import InvalidYoutubeUrlError, TranscriptNotFoundError
from app.core.models import Transcript, TranscriptSegment, VideoMeta


_VIDEO_ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)([0-9A-Za-z_-]{11})")


class YoutubeTranscriptProvider:
    def __init__(self, yt_dlp_path: str | None = None) -> None:
        self.yt_dlp_path = yt_dlp_path

    def get_metadata(self, youtube_url: str) -> VideoMeta:
        opts: dict[str, Any] = {"quiet": True, "noplaylist": True}
        if self.yt_dlp_path:
            opts["youtube_dl_path"] = self.yt_dlp_path

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
        except Exception as exc:
            video_id = extract_video_id(youtube_url)
            if not video_id:
                raise InvalidYoutubeUrlError(str(exc)) from exc
            return VideoMeta(
                video_id=video_id,
                title="YouTube Video",
                uploader=None,
                duration_sec=None,
                webpage_url=f"https://youtu.be/{video_id}",
            )

        video_id = str(info.get("id") or extract_video_id(youtube_url) or "")
        if not video_id:
            raise InvalidYoutubeUrlError()

        return VideoMeta(
            video_id=video_id,
            title=unicodedata.normalize("NFC", str(info.get("title") or "YouTube Video")),
            uploader=info.get("uploader"),
            duration_sec=_optional_int(info.get("duration")),
            webpage_url=str(info.get("webpage_url") or youtube_url),
        )

    def get_transcript(self, youtube_url: str, language: str) -> Transcript:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            raise InvalidYoutubeUrlError()

        languages = _language_candidates(language)
        try:
            entries = _fetch_transcript(video_id, languages)
        except Exception as exc:
            raise TranscriptNotFoundError(str(exc)) from exc

        segments: list[TranscriptSegment] = []
        for entry in entries:
            start = float(entry.get("start", 0.0))
            duration = float(entry.get("duration", 0.0))
            text = _clean_caption(str(entry.get("text", "")))
            if text:
                segments.append(TranscriptSegment(start=start, end=start + duration, text=text))

        raw_text = " ".join(segment.text for segment in segments)
        if not raw_text.strip():
            raise TranscriptNotFoundError()

        return Transcript(
            source="youtube_subtitle",
            language=language,
            segments=segments,
            raw_text=unicodedata.normalize("NFC", raw_text),
        )


def extract_video_id(url: str) -> str | None:
    match = _VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


def _fetch_transcript(video_id: str, languages: list[str]) -> list[dict[str, Any]]:
    api = YouTubeTranscriptApi()
    if hasattr(api, "fetch"):
        fetched = api.fetch(video_id, languages=languages)
        return [dict(item) for item in fetched]
    return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)


def _language_candidates(language: str) -> list[str]:
    candidates = [language]
    if language != "ko":
        candidates.append("ko")
    if "en" not in candidates:
        candidates.append("en")
    return candidates


def _clean_caption(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

