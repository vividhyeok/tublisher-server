from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

from app.core.cancellation import CancellationToken
from app.core.checkpoint import PipelineCheckpointStore
from app.core.content_classifier import classify_content_type
from app.core.density import estimate_source_density
from app.core.draft_guard import ensure_draft_allowed, inspect_draft, sanitize_draft
from app.core.errors import InvalidYoutubeUrlError, JobCancelledError, TranscriptNotFoundError
from app.core.events import EventEmitter, ProgressCallback
from app.core.length_policy import calculate_length_budget
from app.core.models import (
    BookDraft,
    ContentAnalysis,
    GuardReport,
    JobRequest,
    JobResult,
    LengthBudget,
    NarrativePlan,
    SourceDensity,
    Transcript,
    VideoMeta,
)
from app.core.plan_guard import inspect_plan
from app.core.source_coverage import SourceCoverageResult, run_source_coverage_pass
from app.core.serialization import to_plain_dict
from app.providers.audio.base import AudioFallbackProvider
from app.providers.planning.base import PlanningProvider
from app.providers.stt.base import SpeechToTextProvider
from app.providers.transcript.base import TranscriptProvider
from app.providers.writing.base import ChapterWritingProvider, WritingProvider
from app.renderers.epub_builder import EpubBuilder
from app.renderers.html_renderer import markdown_to_html_document
from app.renderers.markdown_renderer import save_markdown


PlanReviewAction = str


@dataclass(frozen=True)
class PlanReviewBundle:
    request: JobRequest
    meta: VideoMeta
    transcript: Transcript
    content_analysis: ContentAnalysis
    density: SourceDensity
    length_budget: LengthBudget
    plan: NarrativePlan
    guard_report: GuardReport


@dataclass(frozen=True)
class PlanReviewResult:
    action: PlanReviewAction
    plan: Optional[NarrativePlan] = None


PlanReviewCallback = Callable[[PlanReviewBundle], PlanReviewResult]


class BookPipeline:
    def __init__(
        self,
        transcript_provider: TranscriptProvider,
        planning_provider: PlanningProvider,
        writing_provider: WritingProvider,
        epub_builder: EpubBuilder,
        audio_provider: Optional[AudioFallbackProvider] = None,
        stt_provider: Optional[SpeechToTextProvider] = None,
        progress_callback: Optional[ProgressCallback] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        self.transcript_provider = transcript_provider
        self.planning_provider = planning_provider
        self.writing_provider = writing_provider
        self.audio_provider = audio_provider
        self.stt_provider = stt_provider
        self.epub_builder = epub_builder
        self.events = EventEmitter(progress_callback)
        self.cancellation_token = cancellation_token or CancellationToken()

    def run(
        self,
        request: JobRequest,
        plan_review_callback: Optional[PlanReviewCallback] = None,
    ) -> JobResult:
        clean_url = _normalize_youtube_url(request.youtube_url)
        if not _looks_like_youtube_url(clean_url):
            raise InvalidYoutubeUrlError()

        checkpoint = PipelineCheckpointStore(
            request_signature={
                "youtube_url": clean_url,
                "language": request.language,
                "output_mode": request.output_mode,
                "prefer_subtitles": request.prefer_subtitles,
                "allow_audio_fallback": request.allow_audio_fallback,
                "narrative_style": request.narrative_style,
                "planning_provider": request.planning_provider,
                "writing_provider": request.writing_provider,
            },
            output_dir=request.output_dir,
            clean_url=clean_url,
        )
        state = checkpoint.load()

        self.events.emit(3, "YouTube 링크 확인 중")
        self.cancellation_token.throw_if_cancelled()

        if state.meta:
            self.events.emit(8, "영상 정보 복원 중 (체크포인트)")
            meta = state.meta
        else:
            self.events.emit(8, "영상 정보 가져오는 중")
            meta = self.transcript_provider.get_metadata(clean_url)
            checkpoint.save_meta(meta)
        self.cancellation_token.throw_if_cancelled()

        if state.transcript:
            self.events.emit(18, "자막/전사 복원 중 (체크포인트)")
            transcript = state.transcript
        else:
            transcript = self._load_transcript(request, clean_url)
            checkpoint.save_transcript(transcript)
        self.cancellation_token.throw_if_cancelled()

        if state.content_analysis:
            self.events.emit(50, "영상 유형 복원 중 (체크포인트)")
            content_analysis = state.content_analysis
        else:
            self.events.emit(50, "영상 유형 분류 중")
            content_analysis = classify_content_type(transcript, meta)
            checkpoint.save_content_analysis(content_analysis)

        if state.density and state.length_budget:
            self.events.emit(55, "영상 밀도/분량 복원 중 (체크포인트)")
            density = state.density
            length_budget = state.length_budget
        else:
            self.events.emit(55, "영상 내용 밀도 분석 중")
            density = estimate_source_density(transcript)
            length_budget = calculate_length_budget(density.transcript_chars, request.output_mode)
            checkpoint.save_density(density)
            checkpoint.save_length_budget(length_budget)

        if state.approved_plan:
            self.events.emit(65, "이전 승인 plan 복원 중 (체크포인트)")
            plan = state.approved_plan
        else:
            plan = self._create_and_review_plan(
                request=request,
                meta=meta,
                transcript=transcript,
                content_analysis=content_analysis,
                density=density,
                length_budget=length_budget,
                plan_review_callback=plan_review_callback,
            )
            checkpoint.save_approved_plan(plan)
        self.cancellation_token.throw_if_cancelled()

        if state.draft:
            self.events.emit(75, "원고 복원 중 (체크포인트)")
            draft = sanitize_draft(state.draft)
        else:
            self.events.emit(75, "승인된 plan으로 원고 작성 중")
            draft = sanitize_draft(self._write_draft(meta, transcript, plan))
            checkpoint.save_draft(draft)

        self.events.emit(80, "원본 커버리지 점검 중")
        coverage_result = run_source_coverage_pass(draft, transcript, plan, length_budget)
        draft = sanitize_draft(coverage_result.draft)

        draft_report = inspect_draft(draft, plan, length_budget)
        if draft_report.is_blocked:
            ensure_draft_allowed(draft, plan, length_budget)
        self.cancellation_token.throw_if_cancelled()

        result = self._persist_outputs(
            request,
            meta,
            plan,
            draft,
            length_budget,
            content_analysis,
            density,
            coverage_result,
        )
        checkpoint.clear()
        return result

    def _load_transcript(self, request: JobRequest, clean_url: str) -> Transcript:
        transcript_error: Exception | None = None
        if request.prefer_subtitles:
            self.events.emit(18, "자막 추출 중")
            try:
                return self.transcript_provider.get_transcript(clean_url, request.language)
            except TranscriptNotFoundError as exc:
                transcript_error = exc

        if not request.allow_audio_fallback:
            raise transcript_error or TranscriptNotFoundError()

        if not self.audio_provider or not self.stt_provider:
            raise TranscriptNotFoundError("자막이 없고 오디오 fallback provider가 설정되지 않았습니다.")

        temp_dir = request.output_dir / ".tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.events.emit(30, "자막이 없어 오디오 다운로드 중")
        audio_path = self.audio_provider.download_audio(clean_url, temp_dir)
        self.cancellation_token.throw_if_cancelled()

        self.events.emit(45, "오디오를 텍스트로 변환 중")
        return self.stt_provider.transcribe(audio_path, request.language)

    def _create_and_review_plan(
        self,
        request: JobRequest,
        meta: VideoMeta,
        transcript: Transcript,
        content_analysis: ContentAnalysis,
        density: SourceDensity,
        length_budget: LengthBudget,
        plan_review_callback: Optional[PlanReviewCallback],
    ) -> NarrativePlan:
        while True:
            self.events.emit(60, "EPUB 집필 계획 생성 중")
            plan = self.planning_provider.create_plan(meta, transcript, content_analysis, density, length_budget)
            plan = replace(
                plan,
                narrative_style=request.narrative_style,
                safety_tags=plan.safety_tags or content_analysis.safety_tags,
            )
            guard_report = inspect_plan(plan, length_budget, density, content_analysis)
            bundle = PlanReviewBundle(
                request=request,
                meta=meta,
                transcript=transcript,
                content_analysis=content_analysis,
                density=density,
                length_budget=length_budget,
                plan=plan,
                guard_report=guard_report,
            )

            self.events.emit(65, "plan 검토 대기 중")
            if plan_review_callback is None:
                if guard_report.is_blocked:
                    raise JobCancelledError("검토 콜백 없이 차단 위험 plan을 승인할 수 없습니다.")
                return plan

            result = plan_review_callback(bundle)
            action = result.action
            if action == "approve":
                return result.plan or plan
            if action == "regenerate":
                self.cancellation_token.throw_if_cancelled()
                continue
            raise JobCancelledError()

    def _write_draft(self, meta: VideoMeta, transcript: Transcript, plan: NarrativePlan) -> BookDraft:
        if _should_write_by_chapter(transcript, plan) and isinstance(self.writing_provider, ChapterWritingProvider):
            chapters: list[str] = []
            total = max(1, len(plan.chapters))
            for index, chapter_plan in enumerate(plan.chapters, start=1):
                percent = 75 + int(10 * (index - 1) / total)
                self.events.emit(percent, f"{index}/{total}장 원고 작성 중")
                self.cancellation_token.throw_if_cancelled()
                chapters.append(
                    self.writing_provider.write_chapter(meta, transcript, plan, chapter_plan)
                )
            markdown = "\n\n".join(chapters)
            return BookDraft(title=plan.title, markdown=markdown, chapters=chapters)

        return self.writing_provider.write_book(meta, transcript, plan)

    def _persist_outputs(
        self,
        request: JobRequest,
        meta: VideoMeta,
        plan: NarrativePlan,
        draft: BookDraft,
        length_budget: LengthBudget,
        content_analysis: ContentAnalysis,
        density: SourceDensity,
        coverage_result: SourceCoverageResult,
    ) -> JobResult:
        output_dir = request.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        title = request.epub_title or plan.title or meta.title
        safe_stem = _safe_filename(title)

        self.events.emit(85, "Markdown 저장 중")
        markdown_path = output_dir / f"{safe_stem}.md"
        save_markdown(markdown_path, meta, plan, draft, length_budget)

        plan_path = output_dir / f"{safe_stem}.plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "meta": to_plain_dict(meta),
                    "content_analysis": to_plain_dict(content_analysis),
                    "density": to_plain_dict(density),
                    "length_budget": to_plain_dict(length_budget),
                    "plan": to_plain_dict(plan),
                    "source_coverage": {
                        "shortfall_detected": coverage_result.shortfall_detected,
                        "missing_concepts": coverage_result.missing_concepts,
                        "action": coverage_result.action,
                        "reason": coverage_result.reason,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.events.emit(90, "HTML 변환 중")
        html_path = output_dir / f"{safe_stem}.html"
        html_document = markdown_to_html_document(draft.markdown, title=title, meta=meta)
        html_path.write_text(html_document, encoding="utf-8")

        self.events.emit(95, "EPUB 생성 중")
        epub_path = output_dir / f"{safe_stem}.epub"
        self.epub_builder.build(
            epub_path=epub_path,
            title=title,
            markdown=draft.markdown,
            meta=meta,
            source_url=meta.webpage_url,
        )

        self.events.emit(100, "완료")
        return JobResult(epub_path=epub_path, markdown_path=markdown_path, html_path=html_path, meta=meta)


def _normalize_youtube_url(url: str) -> str:
    return url.replace("https;", "https://").strip()


def _looks_like_youtube_url(url: str) -> bool:
    return bool(re.search(r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[0-9A-Za-z_-]{11}", url))


def _safe_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    normalized = re.sub(r'[\\/:*?"<>|]+', "_", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:80] or "youtube_epub"


def _should_write_by_chapter(transcript: Transcript, plan: NarrativePlan) -> bool:
    return len(transcript.raw_text) >= 30000 and len(plan.chapters) >= 4
