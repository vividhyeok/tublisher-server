from __future__ import annotations

import re

from app.core.models import Transcript, TranscriptSegment, VideoMeta


_VIDEO_ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)([0-9A-Za-z_-]{11})")


class MockTranscriptProvider:
    def get_metadata(self, youtube_url: str) -> VideoMeta:
        video_id = extract_video_id(youtube_url) or "mockvideo01"
        return VideoMeta(
            video_id=video_id,
            title="Mock YouTube EPUB",
            uploader="Tublisher",
            duration_sec=720,
            webpage_url=youtube_url,
        )

    def get_transcript(self, youtube_url: str, language: str) -> Transcript:
        raw_text = (
            "이 영상은 하나의 복잡한 주제를 독자가 이해하기 쉬운 질문으로 바꾸는 방법을 설명한다. "
            "첫째, 원본 내용에서 핵심 질문을 먼저 찾는다. 둘째, 배경지식은 필요한 만큼만 제공한다. "
            "셋째, 각 장은 질문에서 시작해 설명과 정리로 끝나야 한다. "
            "짧은 영상은 긴 책으로 억지 확장하지 않고, 긴 영상은 챕터별로 나누어 작성한다. "
            "마지막으로 AI가 원본보다 과도하게 상상하지 않도록 분량과 배경지식 비율을 제한한다."
        )
        return Transcript(
            source="youtube_subtitle",
            language=language,
            segments=[TranscriptSegment(start=0, end=90, text=raw_text)],
            raw_text=raw_text,
        )


def extract_video_id(url: str) -> str | None:
    match = _VIDEO_ID_RE.search(url)
    return match.group(1) if match else None
