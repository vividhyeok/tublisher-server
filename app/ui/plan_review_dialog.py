from __future__ import annotations

import json
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.core.orchestrator import PlanReviewBundle
from app.core.serialization import narrative_plan_from_dict, to_plain_dict
from app.ui.view_models import CONTENT_TYPE_LABELS, content_type_label, mode_label, risk_label


class PlanReviewDialog(QDialog):
    def __init__(self, bundle: PlanReviewBundle, parent=None) -> None:
        super().__init__(parent)
        self.bundle = bundle
        self.decision = "cancel"
        self.edited_plan = None

        self.setWindowTitle("Plan 검토")
        self.resize(820, 720)

        self.review = QTextBrowser(self)
        self.review.setOpenExternalLinks(False)
        self.review.setMarkdown(_format_plan_review(bundle))

        self.content_type_combo = QComboBox(self)
        for value, label in CONTENT_TYPE_LABELS.items():
            self.content_type_combo.addItem(label, value)
        index = self.content_type_combo.findData(bundle.plan.content_type)
        if index >= 0:
            self.content_type_combo.setCurrentIndex(index)

        self.editor = QPlainTextEdit(self)
        self.editor.setPlainText(json.dumps(to_plain_dict(bundle.plan), ensure_ascii=False, indent=2))
        self.editor.setVisible(False)

        self.approve_button = QPushButton("이 plan으로 생성", self)
        self.regenerate_button = QPushButton("plan 다시 생성", self)
        self.edit_button = QPushButton("직접 수정", self)
        self.cancel_button = QPushButton("취소", self)

        button_row = QHBoxLayout()
        button_row.addWidget(self.approve_button)
        button_row.addWidget(self.regenerate_button)
        button_row.addWidget(self.edit_button)
        button_row.addStretch(1)
        button_row.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.content_type_combo)
        layout.addWidget(self.review, 3)
        layout.addWidget(self.editor, 2)
        layout.addLayout(button_row)

        self.approve_button.clicked.connect(self._approve)
        self.regenerate_button.clicked.connect(self._regenerate)
        self.edit_button.clicked.connect(self._toggle_editor)
        self.cancel_button.clicked.connect(self.reject)

    def reject(self) -> None:
        self.decision = "cancel"
        super().reject()

    def _approve(self) -> None:
        plan = self.bundle.plan
        if self.editor.isVisible():
            try:
                data = json.loads(self.editor.toPlainText())
                plan = narrative_plan_from_dict(data)
            except Exception as exc:
                QMessageBox.warning(self, "수정 오류", f"수정한 plan JSON을 읽지 못했습니다.\n\n{exc}")
                return
        selected_content_type = self.content_type_combo.currentData()
        if selected_content_type != plan.content_type:
            plan = replace(
                plan,
                content_type=selected_content_type,
                content_type_confidence=1.0,
                content_type_reason="사용자가 Plan Review 화면에서 영상 유형을 수정했습니다.",
            )
        self.edited_plan = plan if plan != self.bundle.plan else None
        self.decision = "approve"
        self.accept()

    def _regenerate(self) -> None:
        self.decision = "regenerate"
        self.accept()

    def _toggle_editor(self) -> None:
        visible = not self.editor.isVisible()
        self.editor.setVisible(visible)
        self.approve_button.setText("수정 plan으로 생성" if visible else "이 plan으로 생성")
        self.resize(self.width(), 880 if visible else 720)


def _format_plan_review(bundle: PlanReviewBundle) -> str:
    plan = bundle.plan
    budget = bundle.length_budget
    report = bundle.guard_report
    analysis = bundle.content_analysis
    lines: list[str] = [
        f"# {plan.title}",
        "",
        f"**부제**: {plan.subtitle}",
        "",
        "## 핵심 질문",
        plan.core_question,
        "",
        "## 영상 유형",
        f"- 분류: {content_type_label(plan.content_type)} / 신뢰도 {plan.content_type_confidence:.2f}",
        f"- 분류 이유: {plan.content_type_reason}",
        f"- 안전 태그: {', '.join(plan.safety_tags) if plan.safety_tags else '없음'}",
        f"- 초기 분석: {content_type_label(analysis.content_type)} / 신뢰도 {analysis.confidence:.2f}",
        f"- 지배 구조: {analysis.dominant_structure}",
        "",
        "## 장르별 주의점",
        *_numbered(plan.caution_points),
        "",
        "## 출력 정보",
        f"- 원본 자막 분량: 약 {budget.source_chars:,}자",
        f"- 예상 EPUB 분량: 약 {plan.target_length_chars:,}자",
        f"- 확장률: {report.expansion_ratio:.2f}배",
        f"- 모드: {mode_label(plan.output_mode)}",
        f"- 분량 위험도: {risk_label(report.risk_level)}",
        "",
    ]

    if report.issues:
        lines.extend(["## 경고", *[f"- {issue.message}" for issue in report.issues], ""])

    if plan.core_axis_left or plan.core_axis_right:
        lines.extend(
            [
                "## 핵심 대립축",
                f"{plan.core_axis_left or '-'} ↔ {plan.core_axis_right or '-'}",
                "",
            ]
        )

    lines.extend(
        [
            "## 읽기 전 필요한 선지식",
            *_numbered(plan.prerequisite_knowledge),
            "",
            "## 전체 흐름",
            *_numbered(plan.narrative_spine),
            "",
            "## 챕터별 설계",
        ]
    )

    for chapter in plan.chapters:
        lines.extend(
            [
                f"### {chapter.order}장. {chapter.title}",
                f"- 시작 질문: {chapter.opening_hook}",
                f"- 핵심 질문: {chapter.key_question}",
                f"- 핵심 개념: {', '.join(chapter.concepts) if chapter.concepts else '-'}",
                f"- 예시: {', '.join(chapter.examples) if chapter.examples else '-'}",
                f"- 예상 분량: {chapter.target_length_chars:,}자",
                f"- 원본/배경 비율: {chapter.source_ratio:.2f} / {chapter.background_ratio:.2f}",
                f"- 다음 장 연결: {chapter.ending_bridge}",
                "",
            ]
        )

    lines.extend(
        [
            "## 읽고 난 뒤 기대 상태",
            plan.expected_reader_after_reading,
            "",
            "## 주의점",
            *_numbered(plan.caution_points),
        ]
    )
    return "\n".join(lines)


def _numbered(items: list[str]) -> list[str]:
    if not items:
        return ["-"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]
