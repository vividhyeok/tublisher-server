from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.density import estimate_source_density
from app.core.length_policy import calculate_length_budget
from app.core.content_classifier import classify_content_type
from app.core.draft_guard import sanitize_draft
from app.core.source_coverage import run_source_coverage_pass
from app.config import default_config
from app.core.checkpoint import PipelineCheckpointStore
from app.core.models import BookDraft, ChapterPlan, JobRequest, LengthBudget, NarrativePlan
from app.core.orchestrator import BookPipeline, PlanReviewResult
from app.providers.planning.json_utils import parse_plan_json
from app.providers.planning.mock_planner import MockPlanningProvider
from app.providers.transcript.mock_provider import MockTranscriptProvider
from app.providers.writing.mock_writer import MockWritingProvider
from app.renderers.epub_builder import _split_markdown_by_h2
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

    def test_health_transcript_detects_health_medical(self) -> None:
        provider = MockTranscriptProvider()
        transcript = provider.get_transcript("https://youtu.be/mockvideo01", "ko")
        health_transcript = type(transcript)(
            source=transcript.source,
            language=transcript.language,
            segments=transcript.segments,
            raw_text=(
                "혈당과 체중 관리에 관한 건강 정보입니다. 식단, 영양, 운동을 설명하지만 "
                "개인차와 전문가 상담이 필요하다는 점을 함께 말합니다."
            ),
        )
        analysis = classify_content_type(health_transcript, provider.get_metadata("https://youtu.be/mockvideo01"))
        self.assertEqual(analysis.content_type, "health_medical")

    def test_service_build_video_prefers_walkthrough_family(self) -> None:
        provider = MockTranscriptProvider()
        transcript = provider.get_transcript("https://youtu.be/mockvideo01", "ko")
        service_transcript = type(transcript)(
            source=transcript.source,
            language=transcript.language,
            segments=transcript.segments,
            raw_text=(
                "서비스 기획부터 요구사항 정리, 화면 설계, API 설계, 배포까지 단계별로 진행합니다. "
                "MVP를 만들고 도메인과 HTTPS를 설정해 출시하는 과정을 따라갑니다."
            ),
        )
        analysis = classify_content_type(service_transcript, provider.get_metadata("https://youtu.be/mockvideo01"))
        self.assertIn(analysis.content_type, {"technical_walkthrough", "service_build_tutorial", "process_tutorial"})

    def test_relationship_psychology_has_mental_health_safety_tag(self) -> None:
        provider = MockTranscriptProvider()
        transcript = provider.get_transcript("https://youtu.be/mockvideo01", "ko")
        rel_transcript = type(transcript)(
            source=transcript.source,
            language=transcript.language,
            segments=transcript.segments,
            raw_text="애착 유형과 관계 패턴, MBTI 궁합의 한계를 개인차 관점에서 설명합니다.",
        )
        analysis = classify_content_type(rel_transcript, provider.get_metadata("https://youtu.be/mockvideo01"))
        self.assertEqual(analysis.content_type, "relationship_psychology")
        self.assertIn("mental_health_sensitive", analysis.safety_tags)

    def test_expert_forecast_has_prediction_tags(self) -> None:
        provider = MockTranscriptProvider()
        transcript = provider.get_transcript("https://youtu.be/mockvideo01", "ko")
        forecast_transcript = type(transcript)(
            source=transcript.source,
            language=transcript.language,
            segments=transcript.segments,
            raw_text="전문가는 향후 10년의 AI 전망과 사회적 변화 시나리오를 제시합니다.",
        )
        analysis = classify_content_type(forecast_transcript, provider.get_metadata("https://youtu.be/mockvideo01"))
        self.assertEqual(analysis.content_type, "expert_forecast")
        self.assertIn("future_prediction", analysis.safety_tags)
        self.assertIn("separate_fact_and_opinion", analysis.safety_tags)


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


class PlanningJsonUtilsTest(unittest.TestCase):
    def test_parse_plan_json_accepts_valid_json_text(self) -> None:
        plan = parse_plan_json('{"title":"테스트","chapters":[]}')
        self.assertEqual(plan.title, "테스트")


class CheckpointStoreTest(unittest.TestCase):
    def test_checkpoint_store_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signature = {"youtube_url": "https://youtu.be/mockvideo01", "output_mode": "balanced"}
            store = PipelineCheckpointStore(signature, Path(tmp), "https://youtu.be/mockvideo01")
            meta = MockTranscriptProvider().get_metadata("https://youtu.be/mockvideo01")
            transcript = MockTranscriptProvider().get_transcript("https://youtu.be/mockvideo01", "ko")

            store.save_meta(meta)
            store.save_transcript(transcript)

            restored = store.load()
            self.assertIsNotNone(restored.meta)
            self.assertIsNotNone(restored.transcript)
            self.assertEqual(restored.meta.video_id, meta.video_id)
            self.assertEqual(restored.transcript.raw_text, transcript.raw_text)


class DraftSanitizeTest(unittest.TestCase):
    def test_sanitize_draft_removes_duplicate_blocks(self) -> None:
        draft = BookDraft(
            title="test",
            markdown="## A\n\n같은 문장\n\n같은 문장\n\n- 안정형\n\n안정형",
            chapters=[],
        )
        cleaned = sanitize_draft(draft)
        self.assertEqual(cleaned.markdown.count("같은 문장"), 1)


class EpubSectionSplitTest(unittest.TestCase):
    def test_split_markdown_by_h2_creates_multiple_sections(self) -> None:
        sections = _split_markdown_by_h2("# 제목\n\n## 첫 장\n본문\n\n## 둘째 장\n본문", "fallback")
        self.assertGreaterEqual(len(sections), 2)
        self.assertEqual(sections[1][0], "첫 장")


class SourceCoveragePassTest(unittest.TestCase):
    def test_shortfall_checks_missing_before_expand(self) -> None:
        transcript = MockTranscriptProvider().get_transcript("https://youtu.be/mockvideo01", "ko")
        plan = NarrativePlan(
            content_type="technical_walkthrough",
            content_type_confidence=0.9,
            content_type_reason="테스트",
            title="테스트",
            subtitle="",
            source_summary="",
            core_question="",
            core_axis_left=None,
            core_axis_right=None,
            prerequisite_knowledge=[],
            narrative_spine=[],
            target_length_chars=5000,
            max_length_chars=10000,
            output_mode="balanced",
            narrative_style="natural",
            source_dependency="high",
            allowed_expansion="",
            safety_tags=["version_policy_may_change"],
            chapters=[
                ChapterPlan(
                    order=1,
                    title="장1",
                    opening_hook="",
                    key_question="",
                    concepts=["핵심 질문"],
                    examples=[],
                    explanation_strategy="problem_solution",
                    target_length_chars=2000,
                    source_ratio=0.8,
                    background_ratio=0.2,
                    middle_checkpoint="",
                    ending_bridge="",
                )
            ],
            expected_reader_after_reading="",
            caution_points=[],
        )
        budget = LengthBudget(4000, 5000, 8000, 2, "balanced", 1.2, 0.25)
        draft = BookDraft(title="테스트", markdown="## 장1\n\n짧은 본문", chapters=[])

        result = run_source_coverage_pass(draft, transcript, plan, budget)
        self.assertTrue(result.shortfall_detected)
        self.assertEqual(result.action, "supplemented_missing_source_content")

    def test_no_missing_keeps_short(self) -> None:
        transcript = MockTranscriptProvider().get_transcript("https://youtu.be/mockvideo01", "ko")
        plan = NarrativePlan(
            content_type="technical_lecture",
            content_type_confidence=0.9,
            content_type_reason="테스트",
            title="테스트",
            subtitle="",
            source_summary="",
            core_question="",
            core_axis_left=None,
            core_axis_right=None,
            prerequisite_knowledge=[],
            narrative_spine=[],
            target_length_chars=5000,
            max_length_chars=10000,
            output_mode="balanced",
            narrative_style="natural",
            source_dependency="high",
            allowed_expansion="",
            safety_tags=[],
            chapters=[
                ChapterPlan(
                    order=1,
                    title="장1",
                    opening_hook="",
                    key_question="",
                    concepts=["핵심"],
                    examples=[],
                    explanation_strategy="brief_summary",
                    target_length_chars=2000,
                    source_ratio=0.8,
                    background_ratio=0.2,
                    middle_checkpoint="",
                    ending_bridge="",
                )
            ],
            expected_reader_after_reading="",
            caution_points=[],
        )
        budget = LengthBudget(4000, 5000, 8000, 2, "balanced", 1.2, 0.25)
        draft = BookDraft(title="테스트", markdown="## 장1\n\n핵심 내용을 이미 포함한 짧은 본문", chapters=[])

        result = run_source_coverage_pass(draft, transcript, plan, budget)
        self.assertEqual(result.action, "kept_short_to_avoid_hallucination")
        self.assertEqual(result.reason, "source_density_low_or_no_missing_core_content")


class WriterPlanFieldReflectionTest(unittest.TestCase):
    def test_mock_writer_reflects_hook_and_bridge(self) -> None:
        provider = MockWritingProvider()
        transcript_provider = MockTranscriptProvider()
        transcript = transcript_provider.get_transcript("https://youtu.be/mockvideo01", "ko")
        meta = transcript_provider.get_metadata("https://youtu.be/mockvideo01")
        chapter = ChapterPlan(
            order=1,
            title="테스트 장",
            opening_hook="왜 이게 중요한가?",
            key_question="무엇이 핵심인가?",
            concepts=["핵심"],
            examples=[],
            explanation_strategy="brief_summary",
            target_length_chars=800,
            source_ratio=0.8,
            background_ratio=0.2,
            middle_checkpoint="중간 정리",
            ending_bridge="다음 장으로 넘어간다",
        )
        plan = NarrativePlan(
            content_type="technical_lecture",
            content_type_confidence=0.9,
            content_type_reason="",
            title="테스트",
            subtitle="",
            source_summary="",
            core_question="",
            core_axis_left=None,
            core_axis_right=None,
            prerequisite_knowledge=[],
            narrative_spine=[],
            target_length_chars=1200,
            max_length_chars=2000,
            output_mode="balanced",
            narrative_style="natural",
            source_dependency="high",
            allowed_expansion="",
            safety_tags=[],
            chapters=[chapter],
            expected_reader_after_reading="",
            caution_points=[],
        )
        text = provider.write_chapter(meta, transcript, plan, chapter)
        self.assertIn(chapter.opening_hook, text)
        self.assertIn(chapter.ending_bridge, text)


if __name__ == "__main__":
    unittest.main()
