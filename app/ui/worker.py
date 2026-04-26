from __future__ import annotations

import traceback
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from app.config import AppConfig
from app.core.cancellation import CancellationToken
from app.core.errors import AppError, JobCancelledError
from app.core.events import ProgressEvent
from app.core.models import JobRequest, NarrativePlan
from app.core.orchestrator import BookPipeline, PlanReviewBundle, PlanReviewResult
from app.providers.registry import (
    create_audio_provider,
    create_planning_provider,
    create_stt_provider,
    create_transcript_provider,
    create_writing_provider,
)
from app.renderers.epub_builder import EpubBuilder


class PipelineWorker(QObject):
    progress = Signal(int, str)
    log = Signal(str)
    plan_ready = Signal(object)
    finished = Signal(object)
    failed = Signal(str, str)

    def __init__(self, request: JobRequest, config: AppConfig, transcript_provider_name: str = "youtube") -> None:
        super().__init__()
        self.request = request
        self.config = config
        self.transcript_provider_name = transcript_provider_name
        self.cancellation_token = CancellationToken()
        self._decision_event = Event()
        self._review_result = PlanReviewResult(action="cancel")

    @Slot()
    def run(self) -> None:
        try:
            transcript_provider = create_transcript_provider(self.config, self.transcript_provider_name)
            planning_provider = create_planning_provider(self.request.planning_provider)
            writing_provider = create_writing_provider(self.request.writing_provider)
            audio_provider = create_audio_provider(self.config) if self.request.allow_audio_fallback else None
            stt_provider = (
                create_stt_provider(self.config.default_stt_provider, self.config)
                if self.request.allow_audio_fallback
                else None
            )
            pipeline = BookPipeline(
                transcript_provider=transcript_provider,
                planning_provider=planning_provider,
                writing_provider=writing_provider,
                audio_provider=audio_provider,
                stt_provider=stt_provider,
                epub_builder=EpubBuilder(),
                progress_callback=self._on_progress,
                cancellation_token=self.cancellation_token,
            )
            result = pipeline.run(self.request, self._review_plan)
            self.finished.emit(result)
        except AppError as exc:
            self.failed.emit(exc.user_message, exc.technical_message or "")
        except Exception as exc:
            self.failed.emit("처리 중 예상하지 못한 오류가 발생했습니다.", f"{exc}\n{traceback.format_exc()}")

    def cancel(self) -> None:
        self.cancellation_token.cancel()
        self.submit_plan_decision("cancel")

    def submit_plan_decision(self, action: str, plan: NarrativePlan | None = None) -> None:
        self._review_result = PlanReviewResult(action=action, plan=plan)
        self._decision_event.set()

    def _on_progress(self, event: ProgressEvent) -> None:
        self.progress.emit(event.percent, event.message)
        self.log.emit(f"{event.percent:>3}%  {event.message}")

    def _review_plan(self, bundle: PlanReviewBundle) -> PlanReviewResult:
        self._decision_event.clear()
        self.plan_ready.emit(bundle)
        while not self._decision_event.wait(0.1):
            if self.cancellation_token.is_cancelled:
                raise JobCancelledError()
        return self._review_result
