from __future__ import annotations


MODE_LABELS = {
    "compact": "압축형",
    "balanced": "균형형",
    "expanded": "확장형",
}

RISK_LABELS = {
    "low": "낮음",
    "medium": "보통",
    "high": "높음",
    "blocked": "차단",
}

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "mock": "Mock",
}

TRANSCRIPT_PROVIDER_LABELS = {
    "youtube": "YouTube 자막",
    "mock": "Mock 자막",
}

CONTENT_TYPE_LABELS = {
    "technical_lecture": "기술 강의",
    "educational_explanation": "교육 설명",
    "news_report": "뉴스 보도",
    "news_commentary": "뉴스 해설",
    "personal_opinion": "개인 의견",
    "interview": "인터뷰",
    "debate": "토론/대담",
    "review_critique": "리뷰/비평",
    "story_essay": "에세이/이야기",
    "mixed": "혼합",
}


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def risk_label(risk: str) -> str:
    return RISK_LABELS.get(risk, risk)


def content_type_label(content_type: str) -> str:
    return CONTENT_TYPE_LABELS.get(content_type, content_type)
