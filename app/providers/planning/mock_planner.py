from __future__ import annotations

from app.core.models import ChapterPlan, ContentAnalysis, LengthBudget, NarrativePlan, SourceDensity, Transcript, VideoMeta


class MockPlanningProvider:
    provider_name = "mock"

    def create_plan(
        self,
        meta: VideoMeta,
        transcript: Transcript,
        content_analysis: ContentAnalysis,
        density: SourceDensity,
        length_budget: LengthBudget,
    ) -> NarrativePlan:
        chapter_count = 2 if density.recommended_output_type == "brief_epub" else length_budget.chapter_count
        per_chapter = max(400, length_budget.target_chars // max(1, chapter_count))
        chapters = [
            ChapterPlan(
                order=index,
                title=_chapter_title(index, density.recommended_output_type),
                opening_hook="이 영상은 어떤 질문에서 출발하는가?",
                key_question=_chapter_question(index),
                concepts=_sample_concepts(transcript.raw_text),
                examples=[],
                explanation_strategy="brief_summary" if density.recommended_output_type == "brief_epub" else "problem_solution",
                target_length_chars=per_chapter,
                source_ratio=0.8,
                background_ratio=min(0.2, length_budget.max_background_ratio),
                middle_checkpoint="지금까지의 핵심을 짧게 정리한다.",
                ending_bridge="다음 장에서는 이 질문이 실제 이해로 어떻게 이어지는지 본다.",
            )
            for index in range(1, chapter_count + 1)
        ]

        return NarrativePlan(
            content_type=content_analysis.content_type,
            content_type_confidence=content_analysis.confidence,
            content_type_reason=content_analysis.reason,
            title=meta.title,
            subtitle="YouTube 내용을 흐름 있는 읽기 자료로 정리",
            source_summary=_summary(transcript.raw_text),
            core_question=_core_question(content_analysis.content_type),
            core_axis_left=_axis_left(content_analysis.content_type),
            core_axis_right=_axis_right(content_analysis.content_type),
            prerequisite_knowledge=_prerequisites(content_analysis.content_type),
            narrative_spine=[chapter.title for chapter in chapters],
            target_length_chars=length_budget.target_chars,
            max_length_chars=length_budget.max_chars,
            output_mode=length_budget.mode,
            source_dependency="high",
            allowed_expansion="원본 이해를 돕는 최소 배경 설명만 허용",
            chapters=chapters,
            expected_reader_after_reading="영상의 핵심 질문과 주요 논지를 짧게 설명할 수 있다.",
            caution_points=content_analysis.caution_points
            + ["원본에 없는 내용을 중심 주장처럼 확장하지 않는다", "짧은 내용은 억지로 늘리지 않는다"],
        )


def _sample_concepts(text: str) -> list[str]:
    words = [word for word in text.replace(".", " ").replace(",", " ").split() if len(word) >= 2]
    return list(dict.fromkeys(words[:5])) or ["핵심 질문"]


def _summary(text: str) -> str:
    clipped = text.strip()[:220]
    return clipped + ("..." if len(text) > 220 else "")


def _chapter_title(index: int, output_type: str) -> str:
    if output_type == "brief_epub":
        titles = ["핵심 질문", "한 장 요약"]
    else:
        titles = ["문제의 등장", "필요한 배경", "핵심 개념", "연결 구조", "현실적 의미", "마무리 정리", "추가 쟁점", "최종 정리"]
    return titles[index - 1] if index <= len(titles) else f"{index}장"


def _chapter_question(index: int) -> str:
    questions = [
        "왜 이 문제가 중요하게 등장했는가?",
        "이해 전에 알아야 할 배경은 무엇인가?",
        "영상이 말하는 핵심 개념은 무엇인가?",
        "각 내용은 어떻게 연결되는가?",
        "이 내용을 현실에서 어떻게 이해해야 하는가?",
        "마지막으로 무엇을 기억해야 하는가?",
    ]
    return questions[index - 1] if index <= len(questions) else "이 장의 핵심 질문은 무엇인가?"


def _core_question(content_type: str) -> str:
    questions = {
        "news_report": "영상 기준으로 무엇이 실제로 확인되고, 아직 불확실한 점은 무엇인가?",
        "news_commentary": "이 영상은 어떤 쟁점을 어떻게 해석하고 있는가?",
        "personal_opinion": "발화자는 무엇을 문제로 느끼고 어떤 메시지를 전하려 하는가?",
        "interview": "질문과 답변을 통해 어떤 관점이 드러나는가?",
        "debate": "참여자들은 어떤 쟁점에서 어떻게 충돌하는가?",
        "review_critique": "발화자는 무엇을 어떤 기준으로 평가하는가?",
        "story_essay": "이 이야기는 어떤 경험과 문제의식을 중심으로 전개되는가?",
    }
    return questions.get(content_type, "이 영상의 핵심 내용을 어떤 흐름으로 이해해야 하는가?")


def _axis_left(content_type: str) -> str:
    return {
        "news_report": "확인된 사실",
        "news_commentary": "영상의 주장",
        "personal_opinion": "발화자의 경험",
        "interview": "질문",
        "debate": "입장 A",
        "review_critique": "긍정 평가",
    }.get(content_type, "원본 핵심")


def _axis_right(content_type: str) -> str:
    return {
        "news_report": "불확실한 점",
        "news_commentary": "반대 관점/확인 필요 지점",
        "personal_opinion": "따져볼 지점",
        "interview": "답변",
        "debate": "입장 B",
        "review_critique": "부정 평가",
    }.get(content_type, "이해를 위한 최소 배경")


def _prerequisites(content_type: str) -> list[str]:
    if content_type in {"news_report", "news_commentary"}:
        return ["영상에서 확인되는 사실과 발화자의 해석을 구분한다", "영상 이후 사실관계가 바뀌었을 수 있다"]
    if content_type == "interview":
        return ["인터뷰어와 응답자의 발화를 구분한다"]
    if content_type == "debate":
        return ["참여자별 입장과 근거를 분리해 읽는다"]
    if content_type == "review_critique":
        return ["취향 판단과 확인 가능한 사실을 구분한다"]
    if content_type in {"personal_opinion", "story_essay"}:
        return ["발화자의 경험은 영상에서 드러나는 범위에서만 해석한다"]
    return ["원본 영상의 주장을 우선한다", "배경지식은 이해에 필요한 만큼만 사용한다"]
