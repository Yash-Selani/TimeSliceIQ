from __future__ import annotations

import inspect
import json
import logging
import os

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.schemas import AnswerBlock, ChatMessage, ChatResponse, Citation
from app.services.chunker import Chunk
from app.services.prompt import (
    SYSTEM_PROMPT,
    GeminiResponseSchema,
    build_prompt_contents,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"


class LLMFailedError(Exception):
    """Raised when LLM synthesis fails or response cannot be parsed."""


def seconds_to_label(seconds: float) -> str:
    """Format seconds into HH:MM:SS (if >= 1h) or MM:SS (if < 1h).

    Examples:
        75.0 -> "01:15"
        3665.0 -> "01:01:05"
        765.0 -> "12:45"
    """
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences if LLM accidentally wraps JSON."""
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    return clean


class Synthesizer:
    """Synthesizes grounded answers from video transcript chunks using Gemini."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self.client = client
        elif api_key is not None:
            self.client = genai.Client(api_key=api_key)
        else:
            env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if env_key:
                self.client = genai.Client(api_key=env_key)
            else:
                self.client = genai.Client()

    async def synthesize(
        self,
        question: str,
        chunks: list[Chunk],
        history: list[ChatMessage] | None = None,
    ) -> ChatResponse:
        """Synthesize an answer with citations from transcript chunks.

        Args:
            question: User inquiry about video content.
            chunks: List of relevant transcript Chunk objects.
            history: Optional conversation history (last turns).

        Returns:
            ChatResponse containing structured answer blocks with validated citations
            and recommended follow-up questions.

        Raises:
            LLMFailedError: When Gemini API fails or response cannot be parsed.
        """
        if not chunks:
            return ChatResponse(
                blocks=[
                    AnswerBlock(
                        text="This is not covered in the video.",
                        cites=[],
                    )
                ],
                follow_ups=[],
            )

        try:
            contents = build_prompt_contents(question, chunks, history)
        except Exception as exc:
            raise LLMFailedError(f"Failed to build prompt contents: {exc}") from exc

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=GeminiResponseSchema,
            temperature=0.1,
        )

        try:
            generate_fn = getattr(self.client.models, "generate_content", None)
            if inspect.iscoroutinefunction(generate_fn):
                response = await self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
        except LLMFailedError:
            raise
        except Exception as exc:
            exc_str = str(exc)
            if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                from app.errors import RateLimitError
                raise RateLimitError(f"Gemini API rate limit exceeded: {exc}") from exc
            raise LLMFailedError(f"Gemini API call failed: {exc}") from exc

        parsed_schema: GeminiResponseSchema | None = None

        # Check if response.parsed was populated by SDK
        if hasattr(response, "parsed") and response.parsed is not None:
            if isinstance(response.parsed, GeminiResponseSchema):
                parsed_schema = response.parsed
            elif isinstance(response.parsed, dict):
                try:
                    parsed_schema = GeminiResponseSchema.model_validate(response.parsed)
                except Exception:
                    parsed_schema = None
            elif hasattr(response.parsed, "answer"):
                try:
                    parsed_schema = GeminiResponseSchema.model_validate(response.parsed)
                except Exception:
                    parsed_schema = None

        # Fallback to response.text parsing
        if parsed_schema is None:
            raw_text = getattr(response, "text", None)
            if not raw_text or not str(raw_text).strip():
                raise LLMFailedError("Gemini returned empty response text.")
            try:
                cleaned_json = _strip_markdown_fences(str(raw_text))
                parsed_schema = GeminiResponseSchema.model_validate_json(cleaned_json)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise LLMFailedError(f"Failed to parse structured JSON from LLM: {exc}") from exc

        chunks_by_id: dict[str, Chunk] = {c.id: c for c in chunks}
        answer_blocks: list[AnswerBlock] = []

        for block in parsed_schema.answer:
            valid_cites: list[Citation] = []
            seen_chunk_ids: set[str] = set()
            for cid in block.cites:
                # If chunk ID exists in provided chunks and hasn't been cited yet in this block
                if cid in chunks_by_id and cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    chunk = chunks_by_id[cid]
                    valid_cites.append(
                        Citation(
                            chunk_id=chunk.id,
                            label=seconds_to_label(chunk.start_s),
                            seconds=chunk.start_s,
                        )
                    )
                # Hallucinated or non-existent chunk IDs are silently dropped

            answer_blocks.append(AnswerBlock(text=block.text, cites=valid_cites))

        if not answer_blocks:
            answer_blocks = [
                AnswerBlock(
                    text="This is not covered in the video.",
                    cites=[],
                )
            ]

        follow_ups: list[str] = []
        if parsed_schema.follow_ups:
            follow_ups = [
                str(q).strip()
                for q in parsed_schema.follow_ups
                if q and str(q).strip()
            ][:3]

        return ChatResponse(blocks=answer_blocks, follow_ups=follow_ups)


__all__ = [
    "DEFAULT_MODEL",
    "LLMFailedError",
    "Synthesizer",
    "seconds_to_label",
]
