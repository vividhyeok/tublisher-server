from __future__ import annotations

import re
from collections import Counter

from app.core.models import OutputMode, OutputType, SourceDensity, Transcript


_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")
_STOPWORDS = {
    "그리고",
    "그러면",
    "하지만",
    "그래서",
    "이것",
    "저것",
    "그것",
    "영상",
    "내용",
    "오늘",
    "진짜",
    "약간",
    "그냥",
    "여러분",
}


def estimate_source_density(transcript: Transcript) -> SourceDensity:
    text = _normalize_text(transcript.raw_text)
    transcript_chars = len(text)
    estimated_tokens = max(1, transcript_chars // 2)
    concepts = _extract_concepts(text)
    repetition_score = _calculate_repetition_score(text)
    recommended_output_type = _recommend_output_type(transcript_chars, len(concepts), repetition_score)
    recommended_mode = _recommend_mode(recommended_output_type, repetition_score)

    return SourceDensity(
        transcript_chars=transcript_chars,
        estimated_tokens=estimated_tokens,
        unique_concepts=len(concepts),
        repetition_score=repetition_score,
        recommended_mode=recommended_mode,
        recommended_output_type=recommended_output_type,
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_concepts(text: str) -> set[str]:
    tokens = [token for token in _TOKEN_RE.findall(text) if token not in _STOPWORDS]
    counts = Counter(tokens)
    min_count = 2 if len(tokens) > 120 else 1
    return {token for token, count in counts.items() if count >= min_count}


def _calculate_repetition_score(text: str) -> float:
    sentences = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if len(part.strip()) >= 12]
    if len(sentences) < 4:
        return 0.0

    normalized = [re.sub(r"\s+", " ", sentence.lower())[:90] for sentence in sentences]
    counts = Counter(normalized)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return min(1.0, repeated / max(1, len(sentences)))


def _recommend_output_type(source_chars: int, unique_concepts: int, repetition_score: float) -> OutputType:
    if source_chars <= 3000 or unique_concepts <= 3 or repetition_score >= 0.45:
        return "brief_epub"
    if source_chars >= 30000:
        return "long_chapter_epub"
    return "chapter_epub"


def _recommend_mode(output_type: OutputType, repetition_score: float) -> OutputMode:
    if output_type == "brief_epub" or repetition_score >= 0.35:
        return "compact"
    return "balanced"

