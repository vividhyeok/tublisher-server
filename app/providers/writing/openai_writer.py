from __future__ import annotations

import os

from openai import OpenAI

from app.core.errors import LlmQuotaExceededError
from app.core.models import BookDraft, ChapterPlan, NarrativePlan, Transcript, VideoMeta
from app.providers.writing.prompts import build_chapter_writing_prompt, build_writing_prompt


class OpenAIWritingProvider:
    provider_name = "openai"

    def __init__(self, api_key: str | None = None, model: str = "gpt-4.1-mini") -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_WRITING_MODEL") or model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def write_book(self, meta: VideoMeta, transcript: Transcript, plan: NarrativePlan) -> BookDraft:
        markdown = self._complete(build_writing_prompt(meta, transcript, plan))
        return BookDraft(title=plan.title, markdown=markdown, chapters=_split_chapters(markdown))

    def write_chapter(self, meta: VideoMeta, transcript: Transcript, plan: NarrativePlan, chapter_plan: ChapterPlan) -> str:
        return self._complete(build_chapter_writing_prompt(meta, transcript, plan, chapter_plan))

    def _complete(self, prompt: str) -> str:
        if not self.client:
            raise LlmQuotaExceededError("OPENAI_API_KEY가 설정되지 않았습니다.")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You write concise Korean Markdown based only on the approved plan."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.35,
            )
        except Exception as exc:
            raise LlmQuotaExceededError(str(exc)) from exc
        return response.choices[0].message.content or ""


def _split_chapters(markdown: str) -> list[str]:
    parts = [part.strip() for part in markdown.split("\n## ") if part.strip()]
    return [parts[0]] + [f"## {part}" for part in parts[1:]] if parts else []

