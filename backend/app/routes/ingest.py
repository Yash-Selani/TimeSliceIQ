from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies import (
    get_chunker,
    get_embedder,
    get_metadata_service,
    get_transcript_fetcher,
    get_url_parser,
    get_vector_store,
)
from app.schemas import ErrorResponse, IngestRequest, IngestResponse
from app.services.chunker import Chunk
from app.services.embedder import GeminiEmbedder
from app.services.metadata import VideoMetadata
from app.services.transcript import group_transcript_lines
from app.services.vector_store import VectorStore

router = APIRouter(tags=["ingest"])


@router.post(
    "/api/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        404: {"model": ErrorResponse, "description": "Captions or video unavailable"},
        502: {"model": ErrorResponse, "description": "Transcript fetch blocked"},
    },
)
@router.post("/ingest", response_model=IngestResponse, include_in_schema=False)
async def ingest_video(
    req: IngestRequest,
    url_parser: Callable[[str], str] = Depends(get_url_parser),
    transcript_fetcher: Callable[..., Any] = Depends(get_transcript_fetcher),
    metadata_service: Callable[..., Any] = Depends(get_metadata_service),
    chunker: Callable[..., list[Chunk]] = Depends(get_chunker),
    embedder: GeminiEmbedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
    app_settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """Ingest a YouTube video URL: parse ID, fetch transcript/metadata, chunk, embed, index."""
    # 1. Validate URL and extract 11-char video_id (raises InvalidURLError on failure)
    video_id = url_parser(req.url)

    # 2. Concurrently fetch metadata and transcript
    metadata_coro = metadata_service(video_id)
    transcript_coro = transcript_fetcher(video_id, proxy_url=app_settings.YT_PROXY_URL)
    metadata: VideoMetadata
    raw_transcript: list[dict]
    metadata, raw_transcript = await asyncio.gather(metadata_coro, transcript_coro)

    if not raw_transcript:
        from app.services.transcript import NoCaptionsError
        raise NoCaptionsError(f"No captions available for video '{video_id}'")

    # 3. Chunk transcript into overlapping semantic windows
    chunks: list[Chunk] = chunker(raw_transcript)

    # 4. Embed chunks and upsert to vector store
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

    # 5. Group raw transcript into lines for frontend display (~10-15s)
    transcript_lines = group_transcript_lines(raw_transcript)

    # 6. Calculate total video duration in seconds
    max_end: float = 0.0
    for c in chunks:
        if c.end_s > max_end:
            max_end = c.end_s
    for seg in raw_transcript:
        start = float(seg.get("start", seg.get("start_s", 0.0)))
        dur = float(seg.get("duration", 0.0))
        if start + dur > max_end:
            max_end = start + dur
    duration_s = int(round(max_end))

    # 7. Extract language code if available
    language = "en"
    if raw_transcript and isinstance(raw_transcript, list):
        first_seg = raw_transcript[0]
        if isinstance(first_seg, dict) and "language" in first_seg:
            language = str(first_seg["language"])

    return IngestResponse(
        video_id=video_id,
        title=metadata.title,
        channel=metadata.channel,
        duration_s=duration_s,
        language=language,
        chunk_count=len(chunks),
        transcript=transcript_lines,
    )
