from __future__ import annotations

from app.core.errors import PlanOverExpandedError
from app.core.models import ContentAnalysis, GuardIssue, GuardReport, LengthBudget, NarrativePlan, RiskLevel, SourceDensity


_RISK_ORDER: dict[RiskLevel, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "blocked": 3,
}


def inspect_plan(
    plan: NarrativePlan,
    budget: LengthBudget,
    density: SourceDensity,
    content_analysis: ContentAnalysis | None = None,
) -> GuardReport:
    issues: list[GuardIssue] = []
    expansion_ratio = plan.target_length_chars / max(1, budget.source_chars)
    risk = _risk_from_expansion(expansion_ratio)

    if plan.target_length_chars > budget.max_chars:
        issues.append(
            GuardIssue(
                code="target_exceeds_max",
                message=f"plan 목표 분량이 허용 상한({budget.max_chars:,}자)을 넘었습니다.",
                risk_level="blocked",
            )
        )

    if plan.max_length_chars > budget.max_chars:
        issues.append(
            GuardIssue(
                code="max_exceeds_budget",
                message="plan의 최대 분량이 length budget 상한을 넘었습니다.",
                risk_level="high",
            )
        )

    over_background = [
        chapter
        for chapter in plan.chapters
        if chapter.background_ratio > budget.max_background_ratio
    ]
    if over_background:
        issues.append(
            GuardIssue(
                code="background_ratio_high",
                message=f"배경지식 비율이 높은 챕터가 {len(over_background)}개 있습니다.",
                risk_level="high",
            )
        )

    if len(plan.chapters) > budget.chapter_count + 2:
        issues.append(
            GuardIssue(
                code="too_many_chapters",
                message="원본 분량에 비해 챕터 수가 많습니다.",
                risk_level="medium",
            )
        )

    if len(plan.prerequisite_knowledge) > 6 and density.recommended_output_type == "brief_epub":
        issues.append(
            GuardIssue(
                code="too_much_prerequisite",
                message="내용이 짧은 영상인데 선지식 항목이 많습니다.",
                risk_level="high",
            )
        )

    if plan.source_dependency == "low" and budget.mode != "expanded":
        issues.append(
            GuardIssue(
                code="low_source_dependency",
                message="원본 의존도가 낮게 설정되어 AI 해설이 과해질 수 있습니다.",
                risk_level="high",
            )
        )

    if plan.content_type_confidence < 0.4:
        issues.append(
            GuardIssue(
                code="low_content_type_confidence",
                message="영상 유형 분류 신뢰도가 낮아 plan 구조가 맞지 않을 수 있습니다.",
                risk_level="medium",
            )
        )

    if content_analysis and plan.content_type != content_analysis.content_type:
        issues.append(
            GuardIssue(
                code="content_type_mismatch",
                message=(
                    "초기 영상 유형 분석과 plan의 영상 유형이 다릅니다. "
                    "Plan Review에서 유형이 맞는지 확인해야 합니다."
                ),
                risk_level="medium",
            )
        )

    if density.recommended_output_type == "brief_epub" and plan.target_length_chars > 3500:
        issues.append(
            GuardIssue(
                code="brief_source_overplanned",
                message="내용 밀도가 낮은 영상에 긴 EPUB 계획이 생성되었습니다.",
                risk_level="high",
            )
        )

    for issue in issues:
        risk = _max_risk(risk, issue.risk_level)

    return GuardReport(risk_level=risk, issues=issues, expansion_ratio=expansion_ratio)


def ensure_plan_allowed(
    plan: NarrativePlan,
    budget: LengthBudget,
    density: SourceDensity,
    content_analysis: ContentAnalysis | None = None,
) -> GuardReport:
    report = inspect_plan(plan, budget, density, content_analysis)
    if report.is_blocked:
        raise PlanOverExpandedError("; ".join(issue.message for issue in report.issues))
    return report


def _risk_from_expansion(expansion_ratio: float) -> RiskLevel:
    if expansion_ratio >= 2.5:
        return "blocked"
    if expansion_ratio >= 1.8:
        return "high"
    if expansion_ratio >= 1.3:
        return "medium"
    return "low"


def _max_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    return left if _RISK_ORDER[left] >= _RISK_ORDER[right] else right
