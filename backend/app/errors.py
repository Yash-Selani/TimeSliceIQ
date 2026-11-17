from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import ERROR_MESSAGES, ErrorCode, ErrorResponse
from app.services.synthesizer import LLMFailedError
from app.services.transcript import (
    NoCaptionsError,
    TranscriptBlockedError,
    TranscriptError,
    VideoUnavailableError,
)
from app.services.url_parser import InvalidURLError

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when client exceeds the allowed request rate."""

    def __init__(
        self,
        message: str = ERROR_MESSAGES[ErrorCode.RATE_LIMITED],
    ) -> None:
        super().__init__(message)
        self.message = message


async def invalid_url_handler(request: Request, exc: InvalidURLError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            code=ErrorCode.INVALID_URL,
            message=ERROR_MESSAGES[ErrorCode.INVALID_URL],
        ).model_dump(),
    )


async def no_captions_handler(request: Request, exc: NoCaptionsError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            code=ErrorCode.NO_CAPTIONS,
            message=ERROR_MESSAGES[ErrorCode.NO_CAPTIONS],
        ).model_dump(),
    )


async def video_unavailable_handler(
    request: Request, exc: VideoUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            code=ErrorCode.VIDEO_UNAVAILABLE,
            message=ERROR_MESSAGES[ErrorCode.VIDEO_UNAVAILABLE],
        ).model_dump(),
    )


async def transcript_blocked_handler(
    request: Request, exc: TranscriptBlockedError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code=ErrorCode.TRANSCRIPT_BLOCKED,
            message=ERROR_MESSAGES[ErrorCode.TRANSCRIPT_BLOCKED],
        ).model_dump(),
    )


async def llm_failed_handler(request: Request, exc: LLMFailedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code=ErrorCode.LLM_FAILED,
            message=ERROR_MESSAGES[ErrorCode.LLM_FAILED],
        ).model_dump(),
    )


async def rate_limited_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            code=ErrorCode.RATE_LIMITED,
            message=ERROR_MESSAGES[ErrorCode.RATE_LIMITED],
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Invalid request parameters.",
        },
    )


async def transcript_error_handler(request: Request, exc: TranscriptError) -> JSONResponse:
    logger.warning("Generic transcript error encountered: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            code=ErrorCode.TRANSCRIPT_BLOCKED,
            message=ERROR_MESSAGES[ErrorCode.TRANSCRIPT_BLOCKED],
        ).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server exception: %s", exc)
    msg = str(exc).strip()
    if not msg:
        msg = "Internal server processing error. Please try again."
    elif len(msg) > 120:
        msg = f"Server error: {type(exc).__name__}. Please try again."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code=ErrorCode.LLM_FAILED,
            message=msg,
        ).model_dump(),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all domain and validation exception handlers on the FastAPI app."""
    app.add_exception_handler(InvalidURLError, invalid_url_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NoCaptionsError, no_captions_handler)  # type: ignore[arg-type]
    app.add_exception_handler(VideoUnavailableError, video_unavailable_handler)  # type: ignore[arg-type]
    app.add_exception_handler(TranscriptBlockedError, transcript_blocked_handler)  # type: ignore[arg-type]
    app.add_exception_handler(TranscriptError, transcript_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(LLMFailedError, llm_failed_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitError, rate_limited_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, global_exception_handler)  # type: ignore[arg-type]
