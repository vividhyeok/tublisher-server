from __future__ import annotations

import unicodedata
from pathlib import Path

from app.core.models import BookDraft, LengthBudget, NarrativePlan, VideoMeta


def save_markdown(
    markdown_path: Path,
    meta: VideoMeta,
    plan: NarrativePlan,
    draft: BookDraft,
    length_budget: LengthBudget,
) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    document = _front_matter(meta, plan, length_budget) + "\n\n" + draft.markdown.strip() + "\n"
    markdown_path.write_text(unicodedata.normalize("NFC", document), encoding="utf-8")


def _front_matter(meta: VideoMeta, plan: NarrativePlan, length_budget: LengthBudget) -> str:
    return "\n".join(
        [
            "---",
            f"title: {plan.title}",
            f"source_url: {meta.webpage_url}",
            f"source_title: {meta.title}",
            f"content_type: {plan.content_type}",
            f"content_type_confidence: {plan.content_type_confidence}",
            f"output_mode: {length_budget.mode}",
            f"target_length_chars: {length_budget.target_chars}",
            f"max_length_chars: {length_budget.max_chars}",
            "---",
        ]
    )
