from __future__ import annotations

from typing import Optional


class AppError(Exception):
    user_message = "작업 중 오류가 발생했습니다."
    recoverable = True

    def __init__(self, technical_message: Optional[str] = None):
        super().__init__(technical_message or self.user_message)
        self.technical_message = technical_message


class InvalidYoutubeUrlError(AppError):
    user_message = "YouTube 링크 형식이 올바르지 않습니다."


class TranscriptNotFoundError(AppError):
    user_message = "이 영상에서 사용할 수 있는 자막을 찾지 못했습니다."


class AudioDownloadError(AppError):
    user_message = "오디오 다운로드에 실패했습니다."


class FfmpegNotFoundError(AppError):
    user_message = "ffmpeg를 찾지 못했습니다. 설정에서 ffmpeg 경로를 확인해주세요."


class SpeechToTextError(AppError):
    user_message = "오디오를 텍스트로 변환하지 못했습니다."


class LlmQuotaExceededError(AppError):
    user_message = "LLM API 사용량 한도를 초과했습니다. 다른 provider를 선택하거나 나중에 다시 시도해주세요."


class LlmResponseFormatError(AppError):
    user_message = "LLM 응답 형식이 올바르지 않습니다. plan을 다시 생성해주세요."


class PlanOverExpandedError(AppError):
    user_message = "생성 계획이 원본 영상에 비해 과도하게 확장되었습니다. plan을 다시 생성해주세요."


class DraftOverExpandedError(AppError):
    user_message = "생성된 원고가 목표 분량을 초과했습니다. 압축 모드로 다시 생성해주세요."


class EpubBuildError(AppError):
    user_message = "EPUB 생성에 실패했습니다. Markdown/HTML 결과는 저장되었는지 확인해주세요."


class JobCancelledError(AppError):
    user_message = "작업이 취소되었습니다."
    recoverable = True

