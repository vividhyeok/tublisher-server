from __future__ import annotations

from typing import Protocol

from app.core.models import ContentAnalysis, LengthBudget, NarrativePlan, SourceDensity, Transcript, VideoMeta


class PlanningProvider(Protocol):
    provider_name: str

    def create_plan(
        self,
        meta: VideoMeta,
        transcript: Transcript,
        content_analysis: ContentAnalysis,
        density: SourceDensity,
        length_budget: LengthBudget,
    ) -> NarrativePlan:
        ...
