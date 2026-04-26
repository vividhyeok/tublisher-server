from __future__ import annotations

import os

from openai import OpenAI

from app.core.errors import LlmQuotaExceededError
from app.core.models import ContentAnalysis, LengthBudget, SourceDensity, Transcript, VideoMeta
from app.providers.planning.json_utils import parse_plan_json
from app.providers.planning.prompts import build_planning_prompt


class OpenAIPlanningProvider:
    provider_name = "openai"

    def __init__(self, api_key: str | None = None, model: str = "gpt-4.1-mini") -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_PLANNING_MODEL") or model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def create_plan(
        self,
        meta: VideoMeta,
        transcript: Transcript,
        content_analysis: ContentAnalysis,
        density: SourceDensity,
        length_budget: LengthBudget,
    ):
        if not self.client:
            raise LlmQuotaExceededError("OPENAI_API_KEY가 설정되지 않았습니다.")
        prompt = build_planning_prompt(meta, transcript, content_analysis, density, length_budget)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You return only valid JSON for an EPUB narrative plan."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            raise LlmQuotaExceededError(str(exc)) from exc
        return parse_plan_json(response.choices[0].message.content or "")
