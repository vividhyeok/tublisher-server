from __future__ import annotations

from app.core.models import ChapterPlan, NarrativePlan, Transcript, VideoMeta


def build_writing_prompt(meta: VideoMeta, transcript: Transcript, plan: NarrativePlan, transcript_limit: int = 36000) -> str:
    return f"""
너는 승인된 Narrative Plan을 바탕으로 EPUB 원고를 작성한다.
모든 영상을 기술 강의나 개념 설명 영상처럼 다루지 말고, plan의 content_type에 맞는 구조로 작성한다.

절대 규칙:
1. plan에 없는 장을 임의로 추가하지 마라.
2. 원본 transcript에 없는 내용을 주된 설명으로 확장하지 마라.
3. 배경지식은 독자가 이해하는 데 필요한 최소한으로만 추가하라.
4. 각 챕터의 대부분은 원본 영상 내용에 기반해야 한다.
5. 비유는 챕터당 최대 1개만 사용한다.
6. 감성적 서론은 금지한다.
7. 철학적 결론을 과장하지 마라.
8. target_length_chars를 초과하지 마라.
9. 내용이 부족하면 억지로 늘리지 말고 짧게 끝내라.
10. 뉴스/시사/의견/전망 영상에서는 사실, 발화자 주장/의견, AI 해석을 구분하라.
11. 건강/정신건강 주제에서는 진단/치료 조언처럼 단정하지 말고 개인차를 반영하라.
12. safety_tags에 future_prediction 또는 separate_fact_and_opinion이 있으면 "영상에서는", "발화자는", "이 관점에 따르면" 표현을 적극적으로 사용하라.

출력 형식:
- Markdown만 출력한다.
- 제목은 #, 챕터는 ##를 사용한다.
- 코드블록으로 감싸지 않는다.
- narrative_style이 structured면 각 장에 "질문/중간 정리/다음으로" 라벨을 명시한다.
- narrative_style이 natural이면 같은 요소를 라벨 없이 첫 문단/중간 문단/마지막 문단에 자연스럽게 녹인다.

영상 제목: {meta.title}
영상 유형: {plan.content_type}
서술 스타일: {plan.narrative_style}
안전 태그: {", ".join(plan.safety_tags) if plan.safety_tags else "없음"}
유형 신뢰도: {plan.content_type_confidence:.2f}
분류 이유: {plan.content_type_reason}
목표 총 분량: {plan.target_length_chars}자
허용 최대 분량: {plan.max_length_chars}자
핵심 질문: {plan.core_question}
장르별 주의점:
{_numbered(plan.caution_points)}

장르별 작성 지침:
{_content_type_rules(plan.content_type)}

전체 흐름:
{_numbered(plan.narrative_spine)}

챕터 계획:
{_chapter_plan_text(plan)}

Transcript:
{_clip_text(transcript.raw_text, transcript_limit)}
""".strip()


def build_chapter_writing_prompt(
    meta: VideoMeta,
    transcript: Transcript,
    plan: NarrativePlan,
    chapter_plan: ChapterPlan,
    transcript_limit: int = 26000,
) -> str:
    return f"""
너는 승인된 Narrative Plan의 특정 챕터 하나만 작성한다.
다른 챕터를 새로 만들지 말고, 아래 챕터 계획에 해당하는 Markdown만 출력한다.

절대 규칙:
1. 원본 transcript와 chapter_plan에 근거해서만 작성한다.
2. 배경지식은 background_ratio 한도 안에서 최소한으로만 사용한다.
3. 목표 분량 {chapter_plan.target_length_chars}자를 넘기지 않는다.
4. 첫 문단은 opening_hook 또는 key_question을 반영한다.
5. 본문 중간에 concepts/examples를 반영한다.
6. 마지막 문단은 middle_checkpoint/ending_bridge를 반영한다.
7. 감성적 서론, 과장된 결론을 쓰지 않는다.
8. safety_tags에 맞는 claim framing을 적용한다.

책 제목: {plan.title}
영상 제목: {meta.title}
영상 유형: {plan.content_type}
서술 스타일: {plan.narrative_style}
안전 태그: {", ".join(plan.safety_tags) if plan.safety_tags else "없음"}
유형 분류 이유: {plan.content_type_reason}
장르별 작성 지침:
{_content_type_rules(plan.content_type)}

챕터: {chapter_plan.order}장. {chapter_plan.title}
시작 질문: {chapter_plan.opening_hook}
핵심 질문: {chapter_plan.key_question}
핵심 개념: {", ".join(chapter_plan.concepts)}
예시: {", ".join(chapter_plan.examples)}
설명 전략: {chapter_plan.explanation_strategy}
source_ratio: {chapter_plan.source_ratio}
background_ratio: {chapter_plan.background_ratio}
중간 정리: {chapter_plan.middle_checkpoint}
다음 장 연결: {chapter_plan.ending_bridge}

Transcript:
{_clip_text(transcript.raw_text, transcript_limit)}
""".strip()


def _chapter_plan_text(plan: NarrativePlan) -> str:
    lines: list[str] = []
    for chapter in plan.chapters:
        lines.append(
            f"{chapter.order}. {chapter.title}\n"
            f"- 질문: {chapter.key_question}\n"
            f"- 개념: {', '.join(chapter.concepts)}\n"
            f"- 목표 분량: {chapter.target_length_chars}자\n"
            f"- 다음 연결: {chapter.ending_bridge}"
        )
    return "\n\n".join(lines)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _content_type_rules(content_type: str) -> str:
    rules = {
        "technical_lecture": "개념 이해, 필요한 선지식, 주요 원리, 예시, 복습 질문 중심으로 구성한다.",
        "educational_explanation": "개념과 관계를 설명하되 선지식은 짧게 제한한다.",
        "technical_walkthrough": "단계 순서를 유지해 구현 과정을 따라가게 만든다.",
        "process_tutorial": "절차를 단계별로 분리해 재현 가능하게 설명한다.",
        "service_build_tutorial": "기획-설계-구현-배포 흐름을 유지하고 단계별 목적을 분명히 쓴다.",
        "project_case_study": "문제-시도-결과-교훈 순서로 작성한다.",
        "tool_review": "기능, 사용 흐름, 장단점, 적용 조건, 추천 대상을 구분해 쓴다.",
        "expert_forecast": "예측/전망은 발화자 관점으로 프레이밍하고 사실과 구분한다.",
        "expert_interview": "질문과 답변의 주체를 명확히 유지한다.",
        "tech_society_commentary": "기술-사회 영향 해설에서 사실/주장/해석을 구분한다.",
        "policy_commentary": "정책 효과를 단정하지 않고 전제 조건을 함께 쓴다.",
        "relationship_psychology": "관계 심리 유형은 경향으로 설명하고 진단처럼 단정하지 않는다.",
        "health_advice": "건강 조언은 개인차와 한계를 함께 쓴다.",
        "personal_essay": "개인 경험을 일반 법칙처럼 확장하지 않는다.",
        "news_report": "핵심 사실, 시간순 전개, 불확실한 점을 중심으로 쓴다.",
        "news_commentary": "발화자의 주장과 근거, 반대 관점, 사실/의견 구분을 중심으로 쓴다.",
        "personal_opinion": "문제의식, 경험, 주장, 공감 지점과 따져볼 지점을 중심으로 쓰되 심리를 단정하지 않는다.",
        "health_medical": "건강 정보는 개인차를 밝히고 진단/치료 조언처럼 단정하지 않는다.",
        "mental_health": "정신건강 주제는 관리/적응/지원 관점으로 쓰고 단정적 표현을 피한다.",
        "interview": "질문과 답변 구조를 보존하고, 인터뷰어와 응답자의 발화를 구분한다.",
        "debate": "참여자별 입장, 근거, 충돌 지점, 합의된 부분과 남은 질문을 구분한다.",
        "review_critique": "리뷰 대상, 평가 기준, 장점, 단점, 추천 대상을 중심으로 쓰되 임의 별점은 추가하지 않는다.",
        "story_essay": "경험과 문제의식의 흐름을 정리하되 없는 서사를 만들지 않는다.",
        "mixed": "강의형 구조 하나로 강제하지 말고, 섞인 장르를 분리해 읽히게 만든다.",
    }
    return rules.get(content_type, rules["mixed"])


def _clip_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return f"{head}\n\n[중간 transcript 생략]\n\n{tail}"
