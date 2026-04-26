from __future__ import annotations

from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QPushButton, QVBoxLayout

from app.config import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("설정")
        form = QFormLayout()
        form.addRow("기본 저장 폴더", QLabel(str(config.output_dir)))
        form.addRow("ffmpeg 경로", QLabel(config.ffmpeg_path))
        form.addRow("기본 plan provider", QLabel(config.default_planning_provider))
        form.addRow("기본 writing provider", QLabel(config.default_writing_provider))
        form.addRow("기본 STT provider", QLabel(config.default_stt_provider))
        form.addRow("OpenAI STT 모델", QLabel(config.openai_stt_model))
        form.addRow("기본 모드", QLabel(config.default_mode))

        close_button = QPushButton("닫기", self)
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(close_button)
