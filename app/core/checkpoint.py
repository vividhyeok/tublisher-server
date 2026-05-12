from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.core.models import (
    BookDraft,
    ContentAnalysis,
    LengthBudget,
    NarrativePlan,
    SourceDensity,
    Transcript,
    TranscriptSegment,
    VideoMeta,
)
from app.core.serialization import narrative_plan_from_dict, to_plain_dict


@dataclass
class CheckpointState:
    meta: Optional[VideoMeta] = None
    transcript: Optional[Transcript] = None
    content_analysis: Optional[ContentAnalysis] = None
    density: Optional[SourceDensity] = None
    length_budget: Optional[LengthBudget] = None
    approved_plan: Optional[NarrativePlan] = None
    draft: Optional[BookDraft] = None


class PipelineCheckpointStore:
    def __init__(self, request_signature: dict[str, Any], output_dir: Path, clean_url: str) -> None:
        self._signature = request_signature
        digest = hashlib.sha1(clean_url.encode("utf-8")).hexdigest()[:16]
        self.path = output_dir / ".resume" / f"{digest}.json"

    def load(self) -> CheckpointState:
        data = self._read()
        if not data:
            return CheckpointState()

        if data.get("signature") != self._signature:
            return CheckpointState()

        stages = data.get("stages", {})
        return CheckpointState(
            meta=_video_meta_from_dict(stages.get("meta")),
            transcript=_transcript_from_dict(stages.get("transcript")),
            content_analysis=_content_analysis_from_dict(stages.get("content_analysis")),
            density=_source_density_from_dict(stages.get("density")),
            length_budget=_length_budget_from_dict(stages.get("length_budget")),
            approved_plan=_narrative_plan_from_dict(stages.get("approved_plan")),
            draft=_book_draft_from_dict(stages.get("draft")),
        )

    def save_meta(self, meta: VideoMeta) -> None:
        self._save_stage("meta", meta)

    def save_transcript(self, transcript: Transcript) -> None:
        self._save_stage("transcript", transcript)

    def save_content_analysis(self, content_analysis: ContentAnalysis) -> None:
        self._save_stage("content_analysis", content_analysis)

    def save_density(self, density: SourceDensity) -> None:
        self._save_stage("density", density)

    def save_length_budget(self, length_budget: LengthBudget) -> None:
        self._save_stage("length_budget", length_budget)

    def save_approved_plan(self, plan: NarrativePlan) -> None:
        self._save_stage("approved_plan", plan)

    def save_draft(self, draft: BookDraft) -> None:
        self._save_stage("draft", draft)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def _read(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_stage(self, stage_name: str, value: Any) -> None:
        current = self._read() or {"signature": self._signature, "stages": {}}
        current["signature"] = self._signature
        stages = current.setdefault("stages", {})
        stages[stage_name] = to_plain_dict(value)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)


def _video_meta_from_dict(data: Any) -> Optional[VideoMeta]:
    if not isinstance(data, dict):
        return None
    duration = data.get("duration_sec")
    return VideoMeta(
        video_id=str(data.get("video_id", "")),
        title=str(data.get("title", "")),
        uploader=_optional_str(data.get("uploader")),
        duration_sec=int(duration) if duration is not None else None,
        webpage_url=str(data.get("webpage_url", "")),
    )


def _transcript_from_dict(data: Any) -> Optional[Transcript]:
    if not isinstance(data, dict):
        return None
    segments_data = data.get("segments", [])
    segments: list[TranscriptSegment] = []
    if isinstance(segments_data, list):
        for item in segments_data:
            if isinstance(item, dict):
                segments.append(
                    TranscriptSegment(
                        start=float(item.get("start", 0)),
                        end=float(item.get("end", 0)),
                        text=str(item.get("text", "")),
                    )
                )
    return Transcript(
        source=str(data.get("source", "youtube_subtitle")),
        language=str(data.get("language", "ko")),
        segments=segments,
        raw_text=str(data.get("raw_text", "")),
    )


def _content_analysis_from_dict(data: Any) -> Optional[ContentAnalysis]:
    if not isinstance(data, dict):
        return None
    caution = data.get("caution_points")
    return ContentAnalysis(
        content_type=str(data.get("content_type", "mixed")),
        confidence=float(data.get("confidence", 0.0)),
        reason=str(data.get("reason", "")),
        dominant_structure=str(data.get("dominant_structure", "mixed")),
        caution_points=[str(item) for item in caution] if isinstance(caution, list) else [],
        safety_tags=[str(item) for item in data.get("safety_tags", [])] if isinstance(data.get("safety_tags"), list) else [],
    )


def _source_density_from_dict(data: Any) -> Optional[SourceDensity]:
    if not isinstance(data, dict):
        return None
    return SourceDensity(
        transcript_chars=int(data.get("transcript_chars", 0)),
        estimated_tokens=int(data.get("estimated_tokens", 0)),
        unique_concepts=int(data.get("unique_concepts", 0)),
        repetition_score=float(data.get("repetition_score", 0.0)),
        recommended_mode=str(data.get("recommended_mode", "balanced")),
        recommended_output_type=str(data.get("recommended_output_type", "chapter_epub")),
    )


def _length_budget_from_dict(data: Any) -> Optional[LengthBudget]:
    if not isinstance(data, dict):
        return None
    return LengthBudget(
        source_chars=int(data.get("source_chars", 0)),
        target_chars=int(data.get("target_chars", 0)),
        max_chars=int(data.get("max_chars", 0)),
        chapter_count=int(data.get("chapter_count", 1)),
        mode=str(data.get("mode", "balanced")),
        expansion_ratio=float(data.get("expansion_ratio", 1.0)),
        max_background_ratio=float(data.get("max_background_ratio", 0.25)),
    )


def _narrative_plan_from_dict(data: Any) -> Optional[NarrativePlan]:
    if not isinstance(data, dict):
        return None
    try:
        return narrative_plan_from_dict(data)
    except Exception:
        return None


def _book_draft_from_dict(data: Any) -> Optional[BookDraft]:
    if not isinstance(data, dict):
        return None
    chapters = data.get("chapters")
    return BookDraft(
        title=str(data.get("title", "Untitled EPUB")),
        markdown=str(data.get("markdown", "")),
        chapters=[str(item) for item in chapters] if isinstance(chapters, list) else [],
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
