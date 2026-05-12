from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import load_config
from app.core.models import JobRequest
from app.ui.log_panel import LogPanel
from app.ui.plan_review_dialog import PlanReviewDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.view_models import MODE_LABELS, NARRATIVE_STYLE_LABELS, PROVIDER_LABELS, TRANSCRIPT_PROVIDER_LABELS
from app.ui.worker import PipelineWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.thread: QThread | None = None
        self.worker: PipelineWorker | None = None

        self.setWindowTitle("Tublisher YouTube EPUB")
        self.resize(860, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")

        self.output_input = QLineEdit(str(self.config.output_dir), self)
        browse_button = QPushButton("폴더 선택", self)
        browse_button.clicked.connect(self._select_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(browse_button)

        self.mode_combo = QComboBox(self)
        for value, label in MODE_LABELS.items():
            self.mode_combo.addItem(label, value)
        self._set_combo_value(self.mode_combo, self.config.default_mode)

        self.narrative_style_combo = QComboBox(self)
        for value, label in NARRATIVE_STYLE_LABELS.items():
            self.narrative_style_combo.addItem(label, value)
        self._set_combo_value(self.narrative_style_combo, self.config.default_narrative_style)

        self.planning_combo = QComboBox(self)
        self.writing_combo = QComboBox(self)
        for value, label in PROVIDER_LABELS.items():
            self.planning_combo.addItem(label, value)
            self.writing_combo.addItem(label, value)
        self._set_combo_value(self.planning_combo, self.config.default_planning_provider)
        self._set_combo_value(self.writing_combo, self.config.default_writing_provider)

        self.transcript_combo = QComboBox(self)
        for value, label in TRANSCRIPT_PROVIDER_LABELS.items():
            self.transcript_combo.addItem(label, value)

        self.language_input = QLineEdit(self.config.default_language, self)
        self.prefer_subtitles_check = QCheckBox("자막 우선", self)
        self.prefer_subtitles_check.setChecked(self.config.prefer_subtitles)
        self.audio_fallback_check = QCheckBox("자막 없으면 오디오 분석", self)
        self.audio_fallback_check.setChecked(self.config.allow_audio_fallback)

        form = QFormLayout()
        form.addRow("YouTube URL", self.url_input)
        form.addRow("저장 폴더", output_row)
        form.addRow("출력 모드", self.mode_combo)
        form.addRow("서술 스타일", self.narrative_style_combo)
        form.addRow("Plan provider", self.planning_combo)
        form.addRow("Writing provider", self.writing_combo)
        form.addRow("Transcript provider", self.transcript_combo)
        form.addRow("언어", self.language_input)
        form.addRow("", self.prefer_subtitles_check)
        form.addRow("", self.audio_fallback_check)

        self.start_button = QPushButton("시작", self)
        self.cancel_button = QPushButton("취소", self)
        self.cancel_button.setEnabled(False)
        self.settings_button = QPushButton("설정", self)
        self.start_button.clicked.connect(self._start)
        self.cancel_button.clicked.connect(self._cancel)
        self.settings_button.clicked.connect(self._show_settings)

        button_row = QHBoxLayout()
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch(1)
        button_row.addWidget(self.settings_button)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.status_label = QLabel("대기 중", self)
        self.log_panel = LogPanel(self)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(button_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_panel, 1)

        container = QWidget(self)
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _select_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.output_input.text())
        if selected:
            self.output_input.setText(selected)

    def _start(self) -> None:
        request = JobRequest(
            youtube_url=self.url_input.text().strip(),
            output_dir=Path(self.output_input.text()).expanduser(),
            writing_provider=self.writing_combo.currentData(),
            planning_provider=self.planning_combo.currentData(),
            language=self.language_input.text().strip() or "ko",
            output_mode=self.mode_combo.currentData(),
            narrative_style=self.narrative_style_combo.currentData(),
            prefer_subtitles=self.prefer_subtitles_check.isChecked(),
            allow_audio_fallback=self.audio_fallback_check.isChecked(),
        )
        self.log_panel.clear()
        self.progress.setValue(0)
        self.status_label.setText("시작 중")
        self._set_running(True)

        self.thread = QThread(self)
        self.worker = PipelineWorker(
            request=request,
            config=self.config,
            transcript_provider_name=self.transcript_combo.currentData(),
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self.log_panel.append)
        self.worker.plan_ready.connect(self._on_plan_ready)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self._set_running(False))
        self.thread.start()

    def _cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
        self.status_label.setText("취소 요청 중")

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.status_label.setText(message)

    def _on_plan_ready(self, bundle) -> None:
        if not self.worker:
            return
        dialog = PlanReviewDialog(bundle, self)
        if dialog.exec() == PlanReviewDialog.Accepted:
            self.worker.submit_plan_decision(dialog.decision, dialog.edited_plan)
        else:
            self.worker.submit_plan_decision("cancel")

    def _on_finished(self, result) -> None:
        self.progress.setValue(100)
        self.status_label.setText("완료")
        QMessageBox.information(
            self,
            "완료",
            f"EPUB 생성이 완료되었습니다.\n\n{result.epub_path}\n\nMarkdown과 HTML도 같은 폴더에 저장했습니다.",
        )

    def _on_failed(self, user_message: str, technical_message: str) -> None:
        self.status_label.setText("오류")
        if technical_message:
            self.log_panel.append(technical_message)
        QMessageBox.warning(self, "오류", user_message)

    def _show_settings(self) -> None:
        SettingsDialog(self.config, self).exec()

    def _set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)


def run() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
