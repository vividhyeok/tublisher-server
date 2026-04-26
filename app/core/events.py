from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ProgressEvent:
    percent: int
    message: str
    detail: Optional[str] = None


ProgressCallback = Callable[[ProgressEvent], None]


class EventEmitter:
    def __init__(self, callback: Optional[ProgressCallback] = None):
        self._callback = callback

    def emit(self, percent: int, message: str, detail: Optional[str] = None) -> None:
        if self._callback:
            self._callback(ProgressEvent(percent, message, detail))

