from __future__ import annotations

import re
from collections import Counter

from app.core.models import ContentAnalysis, ContentType, DominantStructure, SafetyTag, Transcript, VideoMeta


_KEYWORDS: dict[ContentType, tuple[str, ...]] = {
    "technical_lecture": (
        "코드",
        "프로그래밍",
        "파이썬",
        "자바스크립트",
        "api",
        "서버",
        "데이터베이스",
        "모델",
        "설치",
        "구현",
        "함수",
        "클래스",
        "배포",
        "컴포넌트",
        "에러",
    ),
    "educational_explanation": (
        "개념",
        "원리",
        "이해",
        "설명",
        "정리",
        "학습",
        "예시",
        "배경",
        "이론",
        "구조",
    ),
    "technical_walkthrough": (
        "단계",
        "순서",
        "진행",
        "구현 과정",
        "처음부터",
        "완성",
        "따라하기",
    ),
    "process_tutorial": (
        "튜토리얼",
        "가이드",
        "step",
        "절차",
        "프로세스",
        "워크플로우",
    ),
    "service_build_tutorial": (
        "서비스",
        "mvp",
        "기획",
        "요구사항",
        "화면 설계",
        "api 설계",
        "배포",
        "도메인",
        "https",
    ),
    "project_case_study": (
        "프로젝트",
        "회고",
        "문제 해결",
        "결과",
        "교훈",
        "실패",
        "개선",
    ),
    "tool_review": (
        "툴",
        "도구",
        "기능",
        "사용법",
        "workflow",
        "워크플로",
        "실습",
        "데모",
        "화면",
        "업무",
        "자동화",
    ),
    "expert_forecast": (
        "전망",
        "예측",
        "미래",
        "향후",
        "가능성",
        "시나리오",
        "10년",
    ),
    "expert_interview": (
        "인터뷰",
        "질문",
        "답변",
        "박사",
        "연구자",
        "대표",
        "전문가",
    ),
    "tech_society_commentary": (
        "ai",
        "사회",
        "노동시장",
        "규제",
        "윤리",
        "일자리",
        "산업",
    ),
    "policy_commentary": (
        "정책",
        "법안",
        "규제",
        "정부",
        "공공",
        "제도",
    ),
    "relationship_psychology": (
        "관계",
        "연애",
        "애착",
        "유형",
        "갈등",
        "소통",
        "mbti",
    ),
    "health_advice": (
        "식단",
        "영양",
        "다이어트",
        "운동",
        "생활습관",
        "건강 관리",
    ),
    "personal_essay": (
        "에세이",
        "경험",
        "회고",
        "일상",
        "느낀 점",
        "이야기",
    ),
    "news_report": (
        "보도",
        "기자",
        "현장",
        "발생",
        "사건",
        "사고",
        "경찰",
        "검찰",
        "정부 발표",
        "확인됐습니다",
        "오늘",
        "속보",
    ),
    "news_commentary": (
        "논란",
        "쟁점",
        "해설",
        "분석",
        "정치",
        "대통령",
        "정부",
        "여당",
        "야당",
        "정책",
        "선거",
        "주장",
        "관점",
    ),
    "personal_opinion": (
        "저는",
        "제가",
        "제 생각",
        "개인적으로",
        "느꼈",
        "생각합니다",
        "고민",
        "경험",
        "마음",
        "일상",
    ),
    "health_medical": (
        "건강",
        "의학",
        "증상",
        "진단",
        "치료",
        "혈당",
        "체중",
        "식단",
        "운동",
        "영양",
        "질환",
        "약물",
    ),
    "mental_health": (
        "adhd",
        "우울",
        "불안",
        "정신건강",
        "스트레스",
        "감정",
        "주의력",
        "집중",
        "상담",
        "치료",
        "신경발달",
    ),
    "interview": (
        "인터뷰",
        "질문",
        "답변",
        "말씀",
        "어떻게 보세요",
        "어떻게 생각",
        "진행자",
        "게스트",
        "q:",
        "a:",
    ),
    "debate": (
        "토론",
        "반박",
        "찬성",
        "반대",
        "입장",
        "논쟁",
        "패널",
        "상대",
        "동의하지",
        "합의",
    ),
    "review_critique": (
        "리뷰",
        "후기",
        "평가",
        "장점",
        "단점",
        "추천",
        "비추천",
        "가격",
        "제품",
        "영화",
        "책",
        "별점",
    ),
    "story_essay": (
        "이야기",
        "에세이",
        "삶",
        "하루",
        "여행",
        "기억",
        "사연",
        "브이로그",
        "느낀 점",
        "회상",
    ),
    "mixed": (),
}


_STRUCTURE_BY_TYPE: dict[ContentType, DominantStructure] = {
    "technical_lecture": "concept_explanation",
    "educational_explanation": "concept_explanation",
    "technical_walkthrough": "chronological_process",
    "process_tutorial": "chronological_process",
    "service_build_tutorial": "chronological_process",
    "project_case_study": "chronological_event",
    "tool_review": "review_structure",
    "expert_forecast": "argument_analysis",
    "expert_interview": "qna",
    "tech_society_commentary": "argument_analysis",
    "policy_commentary": "argument_analysis",
    "relationship_psychology": "concept_explanation",
    "health_advice": "concept_explanation",
    "personal_essay": "personal_reflection",
    "news_report": "chronological_event",
    "news_commentary": "argument_analysis",
    "personal_opinion": "personal_reflection",
    "health_medical": "concept_explanation",
    "mental_health": "concept_explanation",
    "interview": "qna",
    "debate": "debate_structure",
    "review_critique": "review_structure",
    "story_essay": "personal_reflection",
    "mixed": "mixed",
}


_CAUTIONS_BY_TYPE: dict[ContentType, list[str]] = {
    "technical_lecture": ["개념 설명은 원본 범위를 넘지 않는다", "예시는 원본 이해에 필요한 만큼만 사용한다"],
    "educational_explanation": ["선지식은 짧게 제한한다", "강의형 구조가 맞는지 plan에서 다시 확인한다"],
    "technical_walkthrough": ["단계 순서를 바꾸지 않는다", "원본에 없는 구현 단계를 추가하지 않는다"],
    "process_tutorial": ["절차형 순서를 명확히 유지한다", "필요한 전제조건을 짧게 표시한다"],
    "service_build_tutorial": ["기획/설계/구현/배포 순서를 유지한다", "도구 소개보다 과정 중심으로 작성한다"],
    "project_case_study": ["결과를 과장하지 않는다", "실패/한계를 함께 남긴다"],
    "tool_review": ["기능 설명과 개인 체감 평가를 구분한다", "버전/요금/정책 변화 가능성을 단정하지 않는다"],
    "expert_forecast": ["전망을 사실처럼 단정하지 않는다", "발화자 관점임을 명시한다"],
    "expert_interview": ["질문자/응답자 발화를 구분한다", "응답자의 전망을 사실로 일반화하지 않는다"],
    "tech_society_commentary": ["사실/의견/해석을 구분한다", "반대 관점 가능성을 남긴다"],
    "policy_commentary": ["정책 효과를 단정하지 않는다", "적용 범위와 전제를 분리한다"],
    "relationship_psychology": ["유형을 진단처럼 단정하지 않는다", "개인차를 명시한다"],
    "health_advice": ["치료 조언처럼 단정하지 않는다", "개인차와 전문가 상담 필요성을 표시한다"],
    "personal_essay": ["개인 경험을 일반 법칙으로 확장하지 않는다", "감성 과장을 줄인다"],
    "news_report": ["사실과 해석을 구분한다", "확인되지 않은 내용을 단정하지 않는다", "영상 이후 사실관계가 바뀌었을 수 있음을 남긴다"],
    "news_commentary": ["발화자의 의견을 객관적 사실처럼 쓰지 않는다", "AI가 정치적 결론을 강화하지 않는다", "논쟁 지점을 표시한다"],
    "personal_opinion": ["발화자의 심리를 단정하지 않는다", "없는 서사를 추가하지 않는다", "영상에서 드러나는 범위에서만 해석한다"],
    "health_medical": ["의학적 진단/치료 지시처럼 쓰지 않는다", "개인차와 조건 차이를 명시한다", "필요시 전문가 상담 권고를 부드럽게 포함한다"],
    "mental_health": ["극복 같은 단정 표현을 피하고 관리/적응/지원 관점으로 쓴다", "진단/치료 조언처럼 쓰지 않는다", "개인차와 전문가 상담 필요성을 명시한다"],
    "interview": ["인터뷰어와 응답자의 발화를 구분한다", "응답자의 말을 일반 사실로 바꾸지 않는다"],
    "debate": ["참여자별 입장을 구분한다", "AI가 임의로 승패를 판정하지 않는다"],
    "review_critique": ["취향과 사실을 구분한다", "AI가 임의로 별점이나 결론을 추가하지 않는다"],
    "story_essay": ["개인의 경험을 과도하게 일반화하지 않는다", "감정선을 미화하거나 새 서사를 만들지 않는다"],
    "mixed": ["하나의 강의형 구조로 강제하지 않는다", "섞인 장르를 plan에서 분리해 다룬다"],
}


_SAFETY_RULES: list[tuple[set[ContentType], list[SafetyTag]]] = [
    ({"health_advice", "health_medical"}, ["health_sensitive", "avoid_medical_advice"]),
    ({"mental_health", "relationship_psychology"}, ["mental_health_sensitive", "avoid_diagnosis"]),
    ({"expert_forecast", "news_commentary", "tech_society_commentary", "policy_commentary"}, ["future_prediction", "separate_fact_and_opinion"]),
    ({"tool_review", "technical_walkthrough", "service_build_tutorial"}, ["version_policy_may_change"]),
    ({"personal_opinion", "personal_essay"}, ["personal_claim"]),
    ({"news_commentary", "policy_commentary", "debate"}, ["political_sensitive"]),
]


def classify_content_type(transcript: Transcript, meta: VideoMeta | None = None) -> ContentAnalysis:
    text = _normalize(f"{meta.title if meta else ''} {transcript.raw_text}")
    scores = _score_content_types(text)
    ranked = scores.most_common(2)

    if not ranked or ranked[0][1] == 0:
        content_type: ContentType = "mixed"
        confidence = 0.35
        reason = "특정 장르를 뚜렷하게 가리키는 단서가 부족합니다."
    else:
        top_type, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        total = sum(scores.values())
        margin = top_score - second_score
        if margin <= 1 and top_score < 5:
            content_type = "mixed"
            confidence = 0.45
            reason = f"{top_type} 단서가 있으나 다른 장르 단서와 섞여 있습니다."
        else:
            content_type = top_type
            confidence = min(0.95, 0.45 + (top_score / max(1, total)) * 0.45 + min(0.1, margin * 0.02))
            reason = _reason_for(content_type, top_score)

    return ContentAnalysis(
        content_type=content_type,
        confidence=round(confidence, 2),
        reason=reason,
        dominant_structure=_STRUCTURE_BY_TYPE[content_type],
        caution_points=_CAUTIONS_BY_TYPE[content_type],
        safety_tags=_safety_tags_for(content_type),
    )


def _score_content_types(text: str) -> Counter[ContentType]:
    scores: Counter[ContentType] = Counter()
    for content_type, keywords in _KEYWORDS.items():
        scores[content_type] = sum(_keyword_count(text, keyword) for keyword in keywords)
    return scores


def _keyword_count(text: str, keyword: str) -> int:
    if " " in keyword:
        return text.count(keyword)
    return len(re.findall(re.escape(keyword), text))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _reason_for(content_type: ContentType, score: int) -> str:
    labels = {
        "technical_lecture": "기술 용어와 구현/설치/코드 관련 표현이 반복됩니다.",
        "educational_explanation": "개념, 원리, 예시 중심의 설명 단서가 반복됩니다.",
        "technical_walkthrough": "구현 단계와 진행 순서를 설명하는 단서가 반복됩니다.",
        "process_tutorial": "절차/가이드/튜토리얼 표현이 반복됩니다.",
        "service_build_tutorial": "서비스 기획-설계-구현-배포 흐름 단서가 반복됩니다.",
        "project_case_study": "프로젝트 결과/회고/개선 단서가 반복됩니다.",
        "tool_review": "도구 기능, 사용 흐름, 실무 적용 관련 표현이 반복됩니다.",
        "expert_forecast": "미래 전망/예측/시나리오 표현이 반복됩니다.",
        "expert_interview": "전문가 인터뷰형 질문/답변 단서가 반복됩니다.",
        "tech_society_commentary": "기술과 사회 변화의 해설 단서가 반복됩니다.",
        "policy_commentary": "정책/규제 해설 단서가 반복됩니다.",
        "relationship_psychology": "관계/애착/유형 해석 단서가 반복됩니다.",
        "health_advice": "건강 관리 조언 단서가 반복됩니다.",
        "personal_essay": "개인 경험 기반 서술 단서가 반복됩니다.",
        "news_report": "사건, 보도, 현장, 기관 관련 표현이 반복됩니다.",
        "news_commentary": "쟁점, 주장, 관점, 정치/사회 해설 단서가 반복됩니다.",
        "personal_opinion": "1인칭 경험과 개인적 판단 표현이 반복됩니다.",
        "health_medical": "건강/의학 용어와 증상/치료 관련 표현이 반복됩니다.",
        "mental_health": "정신건강/주의력/감정 관련 표현이 반복됩니다.",
        "interview": "질문과 답변, 진행자/게스트 구조를 암시하는 표현이 반복됩니다.",
        "debate": "입장 충돌, 반박, 찬반 구조를 암시하는 표현이 반복됩니다.",
        "review_critique": "평가 기준, 장단점, 추천 여부를 다루는 표현이 반복됩니다.",
        "story_essay": "개인 경험, 이야기, 회상형 단서가 반복됩니다.",
        "mixed": "여러 장르 단서가 섞여 있습니다.",
    }
    return f"{labels[content_type]} 감지된 장르 단서 수: {score}."


def _safety_tags_for(content_type: ContentType) -> list[SafetyTag]:
    tags: list[SafetyTag] = []
    for types, mapped in _SAFETY_RULES:
        if content_type in types:
            for tag in mapped:
                if tag not in tags:
                    tags.append(tag)
    return tags
