from __future__ import annotations

import json

from app.core.models import ContentAnalysis, LengthBudget, SourceDensity, Transcript, VideoMeta


def build_planning_prompt(
    meta: VideoMeta,
    transcript: Transcript,
    content_analysis: ContentAnalysis,
    density: SourceDensity,
    length_budget: LengthBudget,
    transcript_limit: int = 32000,
) -> str:
    clipped_transcript = _clip_text(transcript.raw_text, transcript_limit)
    schema = {
        "content_type": "technical_lecture|educational_explanation|technical_walkthrough|process_tutorial|service_build_tutorial|project_case_study|tool_review|expert_forecast|expert_interview|tech_society_commentary|policy_commentary|relationship_psychology|health_advice|personal_essay|news_report|news_commentary|personal_opinion|health_medical|mental_health|interview|debate|review_critique|story_essay|mixed",
        "safety_tags": ["health_sensitive|mental_health_sensitive|avoid_diagnosis|avoid_medical_advice|future_prediction|separate_fact_and_opinion|political_sensitive|version_policy_may_change|financial_sensitive|legal_sensitive|personal_claim"],
        "content_type_confidence": "float 0.0-1.0",
        "content_type_reason": "string",
        "title": "string",
        "subtitle": "string",
        "source_summary": "string",
        "core_question": "string",
        "core_axis_left": "string or null",
        "core_axis_right": "string or null",
        "prerequisite_knowledge": ["string"],
        "narrative_spine": ["string"],
        "target_length_chars": "int",
        "max_length_chars": "int",
        "output_mode": "compact|balanced|expanded",
        "narrative_style": "natural|structured",
        "source_dependency": "high|medium|low",
        "allowed_expansion": "string",
        "chapters": [
            {
                "order": "int",
                "title": "string",
                "opening_hook": "string",
                "key_question": "string",
                "concepts": ["string"],
                "examples": ["string"],
                "explanation_strategy": "chronological|cause_effect|contrast_axis|problem_solution|concept_map|brief_summary",
                "target_length_chars": "int",
                "source_ratio": "float 0.0-1.0",
                "background_ratio": "float 0.0-1.0",
                "middle_checkpoint": "string",
                "ending_bridge": "string",
            }
        ],
        "expected_reader_after_reading": "string",
        "caution_points": ["string"],
    }

    return f"""
너는 원본 YouTube transcript를 바탕으로 EPUB 원고의 Narrative Plan만 만든다.
아직 원고를 쓰지 않는다.

목표는 파편적 내용을 하나의 흐름으로 읽히게 만드는 것이다.
특정 작가의 문체를 모방하지 말고, 독자가 길을 잃지 않도록 큰 질문과 연결 구조를 제공한다.
원본보다 과도하게 확장된 교양서를 쓰면 안 된다.
모든 영상을 기술 강의나 지식 설명 영상이라고 가정하지 마라.

절대 규칙:
1. 원본 내용이 부족하면 짧게 끝내라.
2. target_length_chars를 넘기지 마라.
3. 영상에 없는 배경지식은 이해에 꼭 필요한 경우에만 추가하라.
4. 배경지식은 전체 분량의 제한 비율을 넘기지 마라.
5. 비유는 이해가 어려운 개념에만 사용하라.
6. 장황한 서론, 감성적 문장, 철학적 결론을 금지한다.
7. 각 챕터는 질문 -> 설명 -> 정리 -> 다음 연결 구조를 갖는다.
8. 원본 transcript의 핵심 논지를 벗어나지 마라.
9. content_type에 맞는 EPUB 구조를 선택하라.
10. content_type(장르)와 safety_tags(안전 주의점)를 분리해서 설계하라.
10. 뉴스/시사/의견 영상에서는 사실, 발화자 주장, AI의 해석을 구분할 수 있는 plan을 만들어라.
11. 인터뷰/토론에서는 누가 어떤 입장을 말했는지 구분할 수 있는 구조를 만들어라.
12. 리뷰/비평에서는 평가 기준, 장단점, 추천 대상을 중심으로 구조화하라.
13. 건강/의학/정신건강 영상은 진단이나 치료 지시처럼 쓰지 말고, 개인차와 전문가 상담 필요성을 반영하라.
14. 출력은 반드시 JSON 하나만 반환한다. Markdown 코드블록을 쓰지 마라.

영상 유형 분석:
- content_type: {content_analysis.content_type}
- safety_tags: {", ".join(content_analysis.safety_tags) if content_analysis.safety_tags else "없음"}
- confidence: {content_analysis.confidence:.2f}
- reason: {content_analysis.reason}
- dominant_structure: {content_analysis.dominant_structure}
- caution_points: {", ".join(content_analysis.caution_points)}

영상 유형별 구조 지침:
- technical_lecture / educational_explanation: 개념 이해, 선지식, 주요 개념, 예시, 요약, 복습 질문 중심
- technical_walkthrough / process_tutorial / service_build_tutorial: 단계 순서 중심, 절차 재현 가능성 중심
- project_case_study: 문제-시도-결과-교훈 흐름 중심
- tool_review: 기능 소개, 실제 사용 흐름, 장단점, 적용 조건, 추천 대상 중심
- expert_forecast / tech_society_commentary / policy_commentary: 전망과 사실을 구분하는 논점 구조 중심
- expert_interview: 질문-답변 주체 구분 중심
- relationship_psychology: 유형을 단정하지 않는 경향/맥락 설명 중심
- health_advice / health_medical / mental_health: 개인차, 단정 회피, 안전 안내 중심
- news_report: 무슨 일이 있었나, 핵심 사실, 시간순 전개, 관련 인물/기관, 쟁점, 불확실한 점 중심
- news_commentary: 사건, 핵심 질문, 발화자의 주장, 근거, 반대 관점, 사실/의견 구분 중심
- personal_opinion / story_essay: 문제의식, 경험, 주장, 메시지, 공감 지점, 따져볼 지점 중심
- personal_essay: 개인 경험 중심이되 일반화 억제
- interview: 질문, 답변, 반복 관점, 인상적인 주장, 확인 필요 지점 중심
- debate: 참여자별 입장, 주요 쟁점, 근거, 충돌 지점, 합의/남은 질문 중심
- review_critique: 리뷰 대상, 평가 기준, 긍정/부정 평가, 핵심 근거, 추천 대상 중심

영상 정보:
- 제목: {meta.title}
- 채널: {meta.uploader or "알 수 없음"}
- 길이: {meta.duration_sec or "알 수 없음"}초
- 자막 글자 수: {density.transcript_chars}
- 추정 토큰: {density.estimated_tokens}
- 추정 핵심 개념 수: {density.unique_concepts}
- 반복 점수: {density.repetition_score:.2f}
- 추천 출력 유형: {density.recommended_output_type}

분량 정책:
- 모드: {length_budget.mode}
- 목표 분량: {length_budget.target_chars}자
- 허용 최대 분량: {length_budget.max_chars}자
- 권장 챕터 수: {length_budget.chapter_count}
- 최대 배경지식 비율: {length_budget.max_background_ratio:.2f}

JSON schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Transcript:
{clipped_transcript}
""".strip()


def _clip_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return f"{head}\n\n[중간 transcript 생략]\n\n{tail}"
