from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)

    def append(self, message: str) -> None:
        self.text.appendPlainText(message)

    def clear(self) -> None:
        self.text.clear()

