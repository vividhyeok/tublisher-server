from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.models import BookDraft, ChapterPlan, NarrativePlan, Transcript, VideoMeta


class WritingProvider(Protocol):
    provider_name: str

    def write_book(
        self,
        meta: VideoMeta,
        transcript: Transcript,
        plan: NarrativePlan,
    ) -> BookDraft:
        ...


@runtime_checkable
class ChapterWritingProvider(Protocol):
    provider_name: str

    def write_chapter(
        self,
        meta: VideoMeta,
        transcript: Transcript,
        plan: NarrativePlan,
        chapter_plan: ChapterPlan,
    ) -> str:
        ...

