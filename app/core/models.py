from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


OutputMode = Literal["compact", "balanced", "expanded"]
TranscriptSource = Literal["youtube_subtitle", "auto_subtitle", "audio_stt"]
OutputType = Literal["brief_epub", "chapter_epub", "long_chapter_epub"]
ContentType = Literal[
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
]
DominantStructure = Literal[
    "concept_explanation",
    "chronological_event",
    "argument_analysis",
    "personal_reflection",
    "qna",
    "debate_structure",
    "review_structure",
    "mixed",
]
SourceDependency = Literal["high", "medium", "low"]
ExplanationStrategy = Literal[
    "chronological",
    "cause_effect",
    "contrast_axis",
    "problem_solution",
    "concept_map",
    "brief_summary",
]
RiskLevel = Literal["low", "medium", "high", "blocked"]


@dataclass(frozen=True)
class JobRequest:
    youtube_url: str
    output_dir: Path
    writing_provider: str
    planning_provider: str
    language: str = "ko"
    output_mode: OutputMode = "balanced"
    prefer_subtitles: bool = True
    allow_audio_fallback: bool = True
    epub_title: Optional[str] = None


@dataclass(frozen=True)
class VideoMeta:
    video_id: str
    title: str
    uploader: Optional[str]
    duration_sec: Optional[int]
    webpage_url: str


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    source: TranscriptSource
    language: str
    segments: list[TranscriptSegment]
    raw_text: str


@dataclass(frozen=True)
class SourceDensity:
    transcript_chars: int
    estimated_tokens: int
    unique_concepts: int
    repetition_score: float
    recommended_mode: OutputMode
    recommended_output_type: OutputType


@dataclass(frozen=True)
class ContentAnalysis:
    content_type: ContentType
    confidence: float
    reason: str
    dominant_structure: DominantStructure
    caution_points: list[str]


@dataclass(frozen=True)
class LengthBudget:
    source_chars: int
    target_chars: int
    max_chars: int
    chapter_count: int
    mode: OutputMode
    expansion_ratio: float
    max_background_ratio: float


@dataclass(frozen=True)
class ChapterPlan:
    order: int
    title: str
    opening_hook: str
    key_question: str
    concepts: list[str]
    examples: list[str]
    explanation_strategy: ExplanationStrategy
    target_length_chars: int
    source_ratio: float
    background_ratio: float
    middle_checkpoint: str
    ending_bridge: str


@dataclass(frozen=True)
class NarrativePlan:
    content_type: ContentType
    content_type_confidence: float
    content_type_reason: str
    title: str
    subtitle: str
    source_summary: str
    core_question: str
    core_axis_left: Optional[str]
    core_axis_right: Optional[str]
    prerequisite_knowledge: list[str]
    narrative_spine: list[str]
    target_length_chars: int
    max_length_chars: int
    output_mode: OutputMode
    source_dependency: SourceDependency
    allowed_expansion: str
    chapters: list[ChapterPlan]
    expected_reader_after_reading: str
    caution_points: list[str]


@dataclass(frozen=True)
class BookDraft:
    title: str
    markdown: str
    chapters: list[str]


@dataclass(frozen=True)
class JobResult:
    epub_path: Path
    markdown_path: Path
    html_path: Path
    meta: VideoMeta


@dataclass(frozen=True)
class GuardIssue:
    code: str
    message: str
    risk_level: RiskLevel


@dataclass(frozen=True)
class GuardReport:
    risk_level: RiskLevel
    issues: list[GuardIssue]
    expansion_ratio: float

    @property
    def is_blocked(self) -> bool:
        return self.risk_level == "blocked"
