from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import settings
from app.services.chunker import chunk_transcript
from app.services.embedder import GeminiEmbedder
from app.services.metadata import fetch_metadata
from app.services.synthesizer import Synthesizer
from app.services.transcript import fetch_transcript
from app.services.url_parser import parse_youtube_url
from app.services.vector_store import (
    VectorStore,
)
from app.services.vector_store import (
    get_vector_store as create_vector_store,
)

_embedder_instance: GeminiEmbedder | None = None
_vector_store_instance: VectorStore | None = None
_synthesizer_instance: Synthesizer | None = None


def get_url_parser() -> Callable[[str], str]:
    """Dependency provider for YouTube URL parser."""
    return parse_youtube_url


def get_transcript_fetcher() -> Callable[..., Any]:
    """Dependency provider for YouTube transcript fetcher."""
    return fetch_transcript


def get_metadata_service() -> Callable[..., Any]:
    """Dependency provider for video metadata service."""
    return fetch_metadata


def get_chunker() -> Callable[..., Any]:
    """Dependency provider for transcript chunker."""
    return chunk_transcript


def get_embedder() -> GeminiEmbedder:
    """Dependency provider for GeminiEmbedder singleton."""
    global _embedder_instance
    current_key = settings.GEMINI_API_KEY
    current_model = settings.GEMINI_EMBED_MODEL
    if (
        _embedder_instance is None
        or getattr(_embedder_instance, "_cached_api_key", None) != current_key
        or getattr(_embedder_instance, "_cached_model", None) != current_model
    ):
        _embedder_instance = GeminiEmbedder(
            model=current_model,
            api_key=current_key or None,
        )
        setattr(_embedder_instance, "_cached_api_key", current_key)
        setattr(_embedder_instance, "_cached_model", current_model)
    return _embedder_instance


def get_vector_store() -> VectorStore:
    """Dependency provider for VectorStore singleton."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = create_vector_store(settings.VECTOR_BACKEND)
    return _vector_store_instance


def get_synthesizer() -> Synthesizer:
    """Dependency provider for Synthesizer singleton."""
    global _synthesizer_instance
    current_key = settings.GEMINI_API_KEY
    current_model = settings.GEMINI_MODEL
    if (
        _synthesizer_instance is None
        or getattr(_synthesizer_instance, "_cached_api_key", None) != current_key
        or getattr(_synthesizer_instance, "_cached_model", None) != current_model
    ):
        _synthesizer_instance = Synthesizer(
            model=current_model,
            api_key=current_key or None,
        )
        setattr(_synthesizer_instance, "_cached_api_key", current_key)
        setattr(_synthesizer_instance, "_cached_model", current_model)
    return _synthesizer_instance


def reset_dependencies() -> None:
    """Reset cached singleton instances (primarily for testing)."""
    global _embedder_instance, _vector_store_instance, _synthesizer_instance
    _embedder_instance = None
    _vector_store_instance = None
    _synthesizer_instance = None
