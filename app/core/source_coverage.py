from __future__ import annotations

import re
from dataclasses import dataclass, replace

from app.core.models import BookDraft, LengthBudget, NarrativePlan, Transcript


@dataclass(frozen=True)
class SourceCoverageResult:
    draft: BookDraft
    shortfall_detected: bool
    missing_concepts: list[str]
    action: str
    reason: str | None = None


def run_source_coverage_pass(
    draft: BookDraft,
    transcript: Transcript,
    plan: NarrativePlan,
    budget: LengthBudget,
) -> SourceCoverageResult:
    draft_chars = _text_chars(draft.markdown)
    target_threshold = int(budget.target_chars * 0.85)
    if draft_chars >= target_threshold:
        return SourceCoverageResult(
            draft=draft,
            shortfall_detected=False,
            missing_concepts=[],
            action="no_action_needed",
            reason=None,
        )

    expected = _expected_concepts(plan)
    missing = [concept for concept in expected if concept.lower() not in draft.markdown.lower()]
    if not missing:
        return SourceCoverageResult(
            draft=draft,
            shortfall_detected=True,
            missing_concepts=[],
            action="kept_short_to_avoid_hallucination",
            reason="source_density_low_or_no_missing_core_content",
        )

    snippets = _source_snippets_for_concepts(transcript.raw_text, missing, limit=6)
    if not snippets:
        return SourceCoverageResult(
            draft=draft,
            shortfall_detected=True,
            missing_concepts=missing,
            action="kept_short_to_avoid_hallucination",
            reason="source_density_low_or_no_missing_core_content",
        )

    supplement = _build_supplement_markdown(snippets, style=plan.narrative_style)
    merged = draft.markdown.rstrip() + "\n\n" + supplement + "\n"
    covered = [item[0] for item in snippets]
    return SourceCoverageResult(
        draft=replace(draft, markdown=merged),
        shortfall_detected=True,
        missing_concepts=covered,
        action="supplemented_missing_source_content",
        reason="missing_source_backed_concepts_found",
    )


def _text_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _expected_concepts(plan: NarrativePlan) -> list[str]:
    seen: set[str] = set()
    concepts: list[str] = []
    for chapter in plan.chapters:
        for item in [*chapter.concepts, *chapter.examples]:
            cleaned = item.strip()
            if len(cleaned) < 2:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            concepts.append(cleaned)
    return concepts[:20]


def _source_snippets_for_concepts(text: str, concepts: list[str], limit: int) -> list[tuple[str, str]]:
    sentences = _split_sentences(text)
    found: list[tuple[str, str]] = []
    for concept in concepts:
        lowered = concept.lower()
        for sentence in sentences:
            if lowered in sentence.lower():
                found.append((concept, sentence.strip()))
                break
        if len(found) >= limit:
            break
    return found


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def _build_supplement_markdown(snippets: list[tuple[str, str]], style: str) -> str:
    if style == "structured":
        lines = ["## 원본 기반 보강", "", "중간 정리:"]
        for concept, sentence in snippets:
            lines.append(f"- {concept}: {sentence}")
        lines.extend(["", "다음으로: 위 보강 포인트를 기존 챕터 흐름과 연결해 이해한다."])
        return "\n".join(lines)

    lines = ["## 원본 기반 보강 포인트", ""]
    for concept, sentence in snippets:
        lines.append(f"- {concept}: {sentence}")
    return "\n".join(lines)
