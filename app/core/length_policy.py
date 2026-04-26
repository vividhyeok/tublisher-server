from __future__ import annotations

from app.core.models import LengthBudget, OutputMode


def calculate_length_budget(source_chars: int, mode: str) -> LengthBudget:
    output_mode = _coerce_mode(mode)

    if output_mode == "compact":
        ratio = 0.7
        max_background_ratio = 0.15
    elif output_mode == "expanded":
        ratio = 1.7
        max_background_ratio = 0.35
    else:
        ratio = 1.2
        max_background_ratio = 0.25

    safe_source_chars = max(1, source_chars)
    target = int(safe_source_chars * ratio)

    if safe_source_chars < 3000:
        target = min(3000, max(1500, target))

    max_chars = min(max(int(safe_source_chars * 2.0), target), 60000)
    chapter_count = recommend_chapter_count(safe_source_chars)

    return LengthBudget(
        source_chars=safe_source_chars,
        target_chars=target,
        max_chars=max_chars,
        chapter_count=chapter_count,
        mode=output_mode,
        expansion_ratio=ratio,
        max_background_ratio=max_background_ratio,
    )


def recommend_chapter_count(source_chars: int) -> int:
    if source_chars <= 3000:
        return 2
    if source_chars <= 10000:
        return 4
    if source_chars <= 30000:
        return 6
    return 8


def _coerce_mode(mode: str) -> OutputMode:
    if mode in {"compact", "balanced", "expanded"}:
        return mode  # type: ignore[return-value]
    return "balanced"

