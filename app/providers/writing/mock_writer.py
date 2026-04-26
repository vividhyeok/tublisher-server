from __future__ import annotations

from app.core.models import BookDraft, ChapterPlan, NarrativePlan, Transcript, VideoMeta


class MockWritingProvider:
    provider_name = "mock"

    def write_book(self, meta: VideoMeta, transcript: Transcript, plan: NarrativePlan) -> BookDraft:
        chapters = [self.write_chapter(meta, transcript, plan, chapter) for chapter in plan.chapters]
        markdown = f"# {plan.title}\n\n{plan.subtitle}\n\n" + "\n\n".join(chapters)
        return BookDraft(title=plan.title, markdown=markdown, chapters=chapters)

    def write_chapter(
        self,
        meta: VideoMeta,
        transcript: Transcript,
        plan: NarrativePlan,
        chapter_plan: ChapterPlan,
    ) -> str:
        concept_text = ", ".join(chapter_plan.concepts) if chapter_plan.concepts else "핵심 개념"
        source_excerpt = transcript.raw_text[:500].strip()
        genre_note = _genre_note(plan.content_type)
        return f"""## {chapter_plan.order}장. {chapter_plan.title}

{chapter_plan.opening_hook}

이 장의 핵심 질문은 **{chapter_plan.key_question}**이다. {genre_note} 원본 영상에서 반복해서 확인해야 할 단서는 {concept_text}이다.

원본 내용은 다음 방향으로 정리할 수 있다. {source_excerpt}

중간 정리: {chapter_plan.middle_checkpoint}

{chapter_plan.ending_bridge}
"""


def _genre_note(content_type: str) -> str:
    if content_type in {"news_report", "news_commentary"}:
        return "영상에서 확인되는 사실과 발화자의 해석을 구분해 읽어야 한다."
    if content_type in {"personal_opinion", "story_essay"}:
        return "발화자의 경험과 해석은 영상에서 드러나는 범위에서만 다룬다."
    if content_type == "interview":
        return "질문과 답변의 흐름을 보존해야 한다."
    if content_type == "debate":
        return "참여자별 입장 차이를 흐리지 않아야 한다."
    if content_type == "review_critique":
        return "평가 기준과 취향 판단을 구분해야 한다."
    return "원본 중심으로 이해를 돕는 설명만 더한다."
