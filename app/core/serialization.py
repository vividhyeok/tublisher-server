from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from app.core.models import ChapterPlan, NarrativePlan


def to_plain_dict(value: Any) -> Any:
    if is_dataclass(value):
        return to_plain_dict(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_dict(item) for key, item in value.items()}
    return value


def narrative_plan_from_dict(data: dict[str, Any]) -> NarrativePlan:
    chapters = [chapter_plan_from_dict(item) for item in data.get("chapters", [])]
    return NarrativePlan(
        content_type=_choice(
            data.get("content_type"),
            {
                "technical_lecture",
                "educational_explanation",
                "news_report",
                "news_commentary",
                "personal_opinion",
                "interview",
                "debate",
                "review_critique",
                "story_essay",
                "mixed",
            },
            "mixed",
        ),
        content_type_confidence=float(data.get("content_type_confidence", 0.0)),
        content_type_reason=str(data.get("content_type_reason", "")),
        title=str(data.get("title", "Untitled EPUB")),
        subtitle=str(data.get("subtitle", "")),
        source_summary=str(data.get("source_summary", "")),
        core_question=str(data.get("core_question", "")),
        core_axis_left=_optional_str(data.get("core_axis_left")),
        core_axis_right=_optional_str(data.get("core_axis_right")),
        prerequisite_knowledge=_string_list(data.get("prerequisite_knowledge", [])),
        narrative_spine=_string_list(data.get("narrative_spine", [])),
        target_length_chars=int(data.get("target_length_chars", 0)),
        max_length_chars=int(data.get("max_length_chars", 0)),
        output_mode=_choice(data.get("output_mode"), {"compact", "balanced", "expanded"}, "balanced"),
        source_dependency=_choice(data.get("source_dependency"), {"high", "medium", "low"}, "high"),
        allowed_expansion=str(data.get("allowed_expansion", "")),
        chapters=chapters,
        expected_reader_after_reading=str(data.get("expected_reader_after_reading", "")),
        caution_points=_string_list(data.get("caution_points", [])),
    )


def chapter_plan_from_dict(data: dict[str, Any]) -> ChapterPlan:
    return ChapterPlan(
        order=int(data.get("order", 1)),
        title=str(data.get("title", "Chapter")),
        opening_hook=str(data.get("opening_hook", "")),
        key_question=str(data.get("key_question", "")),
        concepts=_string_list(data.get("concepts", [])),
        examples=_string_list(data.get("examples", [])),
        explanation_strategy=_choice(
            data.get("explanation_strategy"),
            {
                "chronological",
                "cause_effect",
                "contrast_axis",
                "problem_solution",
                "concept_map",
                "brief_summary",
            },
            "brief_summary",
        ),
        target_length_chars=int(data.get("target_length_chars", 0)),
        source_ratio=float(data.get("source_ratio", 0.8)),
        background_ratio=float(data.get("background_ratio", 0.2)),
        middle_checkpoint=str(data.get("middle_checkpoint", "")),
        ending_bridge=str(data.get("ending_bridge", "")),
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _choice(value: Any, choices: set[str], default: str) -> Any:
    text = str(value)
    return text if text in choices else default
