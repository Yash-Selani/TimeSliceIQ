from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import tenacity
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-embedding-001"


def _extract_embedding_values(e: Any) -> list[float]:
    """Safely extract float embedding values from SDK objects, dicts, or lists."""
    if isinstance(e, dict):
        raw = e.get("values", [])
        return [float(x) for x in raw]
    if hasattr(e, "values") and not callable(e.values) and e.values is not None:
        return [float(x) for x in e.values]
    if isinstance(e, list | tuple):
        return [float(x) for x in e]
    return []


class GeminiEmbedder:
    """Service for generating text embeddings using Google Gemini API."""

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

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def _embed_batch_sync(self, batch: list[str]) -> types.EmbedContentResponse:
        """Call synchronous embed_content API with retry on failure."""
        return self.client.models.embed_content(
            model=self.model,
            contents=batch,
        )

    # Alias to allow flexible internal references
    _call_embed_content = _embed_batch_sync

    async def embed_batch(
        self, texts: list[str], batch_size: int = 100
    ) -> list[list[float]]:
        """Embed a list of texts in chunks of at most batch_size."""
        if not texts:
            return []

        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = await asyncio.to_thread(self._embed_batch_sync, batch)
            except Exception as exc:
                exc_str = str(exc)
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    from app.errors import RateLimitError
                    raise RateLimitError(f"Gemini API rate limit exceeded: {exc}") from exc
                raise
            embeddings = getattr(response, "embeddings", None)
            if embeddings:
                batch_embeddings = [_extract_embedding_values(e) for e in embeddings]
                all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        embeddings = await self.embed_batch([text])
        if not embeddings:
            return []
        return embeddings[0]


__all__ = ["GeminiEmbedder"]
