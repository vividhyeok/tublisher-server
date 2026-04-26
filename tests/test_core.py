from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.density import estimate_source_density
from app.core.length_policy import calculate_length_budget
from app.core.content_classifier import classify_content_type
from app.config import default_config
from app.core.models import JobRequest
from app.core.orchestrator import BookPipeline, PlanReviewResult
from app.providers.planning.mock_planner import MockPlanningProvider
from app.providers.transcript.mock_provider import MockTranscriptProvider
from app.providers.writing.mock_writer import MockWritingProvider
from app.renderers.epub_builder import EpubBuilder


class LengthPolicyTest(unittest.TestCase):
    def test_balanced_budget_uses_default_ratio(self) -> None:
        budget = calculate_length_budget(10000, "balanced")
        self.assertEqual(budget.target_chars, 12000)
        self.assertEqual(budget.chapter_count, 4)
        self.assertEqual(budget.mode, "balanced")

    def test_short_source_target_stays_within_max(self) -> None:
        budget = calculate_length_budget(500, "compact")
        self.assertGreaterEqual(budget.max_chars, budget.target_chars)


class ConfigTest(unittest.TestCase):
    def test_default_generation_stack_uses_openai(self) -> None:
        config = default_config()
        self.assertEqual(config.default_planning_provider, "openai")
        self.assertEqual(config.default_writing_provider, "openai")
        self.assertEqual(config.default_stt_provider, "openai")


class DensityTest(unittest.TestCase):
    def test_short_transcript_recommends_brief_epub(self) -> None:
        transcript = MockTranscriptProvider().get_transcript("https://youtu.be/mockvideo01", "ko")
        density = estimate_source_density(transcript)
        self.assertEqual(density.recommended_output_type, "brief_epub")


class ContentClassifierTest(unittest.TestCase):
    def test_review_transcript_is_not_forced_to_technical_lecture(self) -> None:
        provider = MockTranscriptProvider()
        transcript = provider.get_transcript("https://youtu.be/mockvideo01", "ko")
        review_transcript = type(transcript)(
            source=transcript.source,
            language=transcript.language,
            segments=transcript.segments,
            raw_text=(
                "이 제품을 일주일 써본 후기입니다. 장점은 가격 대비 성능이고 단점은 배터리입니다. "
                "추천할 만한 사람과 비추천할 사람을 나눠 평가해보겠습니다."
            ),
        )
        analysis = classify_content_type(review_transcript, provider.get_metadata("https://youtu.be/mockvideo01"))
        self.assertEqual(analysis.content_type, "review_critique")
        self.assertEqual(analysis.dominant_structure, "review_structure")


class PipelineTest(unittest.TestCase):
    def test_mock_pipeline_requires_plan_review_and_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = JobRequest(
                youtube_url="https://youtu.be/mockvideo01",
                output_dir=Path(tmp),
                writing_provider="mock",
                planning_provider="mock",
            )
            reviewed = []
            pipeline = BookPipeline(
                transcript_provider=MockTranscriptProvider(),
                planning_provider=MockPlanningProvider(),
                writing_provider=MockWritingProvider(),
                epub_builder=EpubBuilder(),
            )
            result = pipeline.run(
                request,
                plan_review_callback=lambda bundle: reviewed.append(bundle) or PlanReviewResult("approve"),
            )
            self.assertEqual(len(reviewed), 1)
            self.assertEqual(reviewed[0].plan.content_type, reviewed[0].content_analysis.content_type)
            self.assertTrue(result.markdown_path.exists())
            self.assertTrue(result.html_path.exists())
            self.assertTrue(result.epub_path.exists())


if __name__ == "__main__":
    unittest.main()
