from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace

from app.core.errors import DraftOverExpandedError
from app.core.models import BookDraft, GuardIssue, GuardReport, LengthBudget, NarrativePlan, RiskLevel
from app.core.plan_guard import _RISK_ORDER


_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
_EMOTIONAL_WORDS = ("놀라운", "감동", "운명", "경이", "위대한", "충격", "전율", "혁명적")
_SENSITIVE_ASSERTIVE_PATTERNS = (
    r"반드시",
    r"무조건",
    r"확실히",
    r"완치",
    r"치료된다",
    r"극복해야",
)


def inspect_draft(draft: BookDraft, plan: NarrativePlan, budget: LengthBudget) -> GuardReport:
    markdown_chars = len(re.sub(r"\s+", "", draft.markdown))
    expansion_ratio = markdown_chars / max(1, budget.source_chars)
    issues: list[GuardIssue] = []
    risk: RiskLevel = _risk_from_draft_size(markdown_chars, budget)

    if markdown_chars > budget.max_chars:
        issues.append(
            GuardIssue(
                code="draft_exceeds_max",
                message=f"원고가 허용 상한({budget.max_chars:,}자)을 넘었습니다.",
                risk_level="blocked",
            )
        )

    extra_heading_count = _count_unplanned_headings(draft.markdown, plan)
    if extra_heading_count > 2:
        issues.append(
            GuardIssue(
                code="unplanned_headings",
                message=f"plan에 없는 제목이 {extra_heading_count}개 이상 감지되었습니다.",
                risk_level="medium",
            )
        )

    emotional_count = sum(draft.markdown.count(word) for word in _EMOTIONAL_WORDS)
    if emotional_count >= 5:
        issues.append(
            GuardIssue(
                code="emotional_overwrite",
                message="감성적이거나 과장된 표현이 반복됩니다.",
                risk_level="medium",
            )
        )

    repetition_score = _paragraph_repetition_score(draft.markdown)
    if repetition_score >= 0.25:
        issues.append(
            GuardIssue(
                code="high_repetition",
                message="같은 문단 구조나 내용 반복이 많습니다.",
                risk_level="medium",
            )
        )

    if plan.content_type in {"health_medical", "mental_health"}:
        assertive_hits = _assertive_phrase_hits(draft.markdown)
        if assertive_hits >= 2:
            issues.append(
                GuardIssue(
                    code="sensitive_topic_assertive_tone",
                    message="건강/정신건강 주제에서 단정적 표현이 반복됩니다.",
                    risk_level="medium",
                )
            )

    for issue in issues:
        risk = _max_risk(risk, issue.risk_level)

    return GuardReport(risk_level=risk, issues=issues, expansion_ratio=expansion_ratio)


def ensure_draft_allowed(draft: BookDraft, plan: NarrativePlan, budget: LengthBudget) -> GuardReport:
    report = inspect_draft(draft, plan, budget)
    if report.is_blocked:
        raise DraftOverExpandedError("; ".join(issue.message for issue in report.issues))
    return report


def _risk_from_draft_size(markdown_chars: int, budget: LengthBudget) -> RiskLevel:
    if markdown_chars > budget.max_chars:
        return "blocked"
    if markdown_chars > int(budget.target_chars * 1.25):
        return "high"
    if markdown_chars > int(budget.target_chars * 1.1):
        return "medium"
    return "low"


def _count_unplanned_headings(markdown: str, plan: NarrativePlan) -> int:
    headings = [heading.strip() for heading in _HEADING_RE.findall(markdown)]
    planned = {chapter.title.strip() for chapter in plan.chapters}
    planned.add(plan.title.strip())
    return sum(1 for heading in headings if heading not in planned)


def _paragraph_repetition_score(markdown: str) -> float:
    paragraphs = [part.strip() for part in markdown.split("\n\n") if len(part.strip()) >= 30]
    if len(paragraphs) < 4:
        return 0.0
    signatures = [re.sub(r"\s+", " ", paragraph)[:80] for paragraph in paragraphs]
    counts = Counter(signatures)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / max(1, len(paragraphs))


def _max_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    return left if _RISK_ORDER[left] >= _RISK_ORDER[right] else right


def sanitize_draft(draft: BookDraft) -> BookDraft:
    cleaned_markdown = _deduplicate_markdown_blocks(draft.markdown)
    if cleaned_markdown == draft.markdown:
        return draft
    cleaned_chapters = [_deduplicate_markdown_blocks(chapter) for chapter in draft.chapters]
    return replace(draft, markdown=cleaned_markdown, chapters=cleaned_chapters)


def _deduplicate_markdown_blocks(markdown: str) -> str:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", markdown) if block.strip()]
    seen: set[str] = set()
    kept: list[str] = []

    for block in blocks:
        sig = _block_signature(block)
        if sig and sig in seen:
            continue
        if kept and sig and _is_list_block(kept[-1]) and not _is_list_block(block):
            if _block_signature(kept[-1]) == sig:
                continue
        if sig:
            seen.add(sig)
        kept.append(block)

    return "\n\n".join(kept).strip() + ("\n" if kept else "")


def _block_signature(block: str) -> str:
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", block)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _is_list_block(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return False
    return all(re.match(r"^([-*+]\s+|\d+\.\s+)", line) for line in lines)


def _assertive_phrase_hits(markdown: str) -> int:
    lowered = markdown.lower()
    return sum(len(re.findall(pattern, lowered)) for pattern in _SENSITIVE_ASSERTIVE_PATTERNS)

