from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies import (
    get_chunker,
    get_embedder,
    get_synthesizer,
    get_transcript_fetcher,
    get_vector_store,
)
from app.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.chunker import Chunk
from app.services.embedder import GeminiEmbedder
from app.services.retriever import retrieve_chunks
from app.services.synthesizer import Synthesizer
from app.services.vector_store import VectorStore

router = APIRouter(tags=["chat"])

_indexing_locks: dict[str, asyncio.Lock] = {}


async def ensure_indexed(
    video_id: str,
    store: VectorStore,
    embedder: GeminiEmbedder,
    transcript_fetcher: Callable[..., Any],
    chunker: Callable[..., list[Chunk]],
    proxy_url: str | None = None,
) -> None:
    """Ensure vector collection exists for video_id; auto-index if missing."""
    if await store.has_collection(video_id):
        return

    lock = _indexing_locks.setdefault(video_id, asyncio.Lock())
    async with lock:
        if await store.has_collection(video_id):
            return

        raw_transcript = await transcript_fetcher(video_id, proxy_url=proxy_url)
        if not raw_transcript:
            from app.services.transcript import NoCaptionsError
            raise NoCaptionsError(f"No captions available for video '{video_id}'")
        chunks = chunker(raw_transcript)
        await store.create_collection(video_id)
        if chunks:
            chunk_texts = [c.text for c in chunks]
            try:
                embeddings = await embedder.embed_batch(chunk_texts)
            except Exception as exc:
                exc_str = str(exc)
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    from app.errors import RateLimitError
                    raise RateLimitError(f"Gemini embedding rate limit exceeded: {exc}") from exc
                from app.services.synthesizer import LLMFailedError
                raise LLMFailedError(f"Failed to generate embeddings: {exc}") from exc
            ids = [c.id for c in chunks]
            metadatas = [{"start_s": c.start_s, "end_s": c.end_s} for c in chunks]
            await store.upsert(
                collection_name=video_id,
                ids=ids,
                texts=chunk_texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Captions or video unavailable"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "LLM or transcript error"},
    },
)
@router.post("/chat", response_model=ChatResponse, include_in_schema=False)
async def chat_with_video(
    req: ChatRequest,
    store: VectorStore = Depends(get_vector_store),
    embedder: GeminiEmbedder = Depends(get_embedder),
    synthesizer: Synthesizer = Depends(get_synthesizer),
    transcript_fetcher: Callable[..., Any] = Depends(get_transcript_fetcher),
    chunker: Callable[..., list[Chunk]] = Depends(get_chunker),
    app_settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Ask a question about a video and receive grounded answers with timestamped citations."""
    # 1. Idempotently ensure collection is indexed in vector store
    await ensure_indexed(
        video_id=req.video_id,
        store=store,
        embedder=embedder,
        transcript_fetcher=transcript_fetcher,
        chunker=chunker,
        proxy_url=app_settings.YT_PROXY_URL,
    )

    # 2. Retrieve top-k relevant chunks (default top_k=8)
    chunks = await retrieve_chunks(
        store=store,
        embedder=embedder,
        video_id=req.video_id,
        query=req.question,
        top_k=8,
    )

    # 3. Grounded synthesis using Gemini
    response = await synthesizer.synthesize(
        question=req.question,
        chunks=chunks,
        history=req.history,
    )

    return response
