from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    NO_CAPTIONS = "NO_CAPTIONS"
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    TRANSCRIPT_BLOCKED = "TRANSCRIPT_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    LLM_FAILED = "LLM_FAILED"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_URL: "Please paste a valid YouTube link.",
    ErrorCode.NO_CAPTIONS: "This video doesn't have captions available.",
    ErrorCode.VIDEO_UNAVAILABLE: "This video is private, deleted, or otherwise unavailable.",
    ErrorCode.TRANSCRIPT_BLOCKED: (
        "YouTube blocked the transcript request. Try again or configure a proxy."
    ),
    ErrorCode.RATE_LIMITED: "Too many requests. Please wait a moment.",
    ErrorCode.LLM_FAILED: "The AI couldn't process your question. Please try again.",
}


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str


class IngestRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL", min_length=1, max_length=2048)


class TranscriptLine(BaseModel):
    start_s: float = Field(..., description="Start time in seconds")
    text: str


class IngestResponse(BaseModel):
    video_id: str = Field(..., description="11-character YouTube video ID")
    title: str
    channel: str
    duration_s: int = Field(..., description="Video duration in seconds")
    language: str = Field(..., description="Transcript language code")
    chunk_count: int = Field(..., description="Number of indexed chunks")
    transcript: list[TranscriptLine] = Field(
        ..., description="Transcript grouped into ~10-15s lines"
    )


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    video_id: str = Field(..., description="11-character YouTube video ID")
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=6)


class Citation(BaseModel):
    chunk_id: str = Field(..., description="Chunk identifier like 'c0', 'c17'")
    label: str = Field(..., description="Human-readable timestamp like '12:45'")
    seconds: float = Field(..., description="Timestamp in seconds")


class AnswerBlock(BaseModel):
    text: str
    cites: list[Citation] = Field(default_factory=list)


class ChatResponse(BaseModel):
    blocks: list[AnswerBlock]
    follow_ups: list[str] = Field(default_factory=list, max_length=3)
