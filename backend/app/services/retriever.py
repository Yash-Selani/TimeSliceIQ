from __future__ import annotations

import inspect
from typing import Any

from app.services.vector_store import QueryResult, VectorStore

from app.services.chunker import Chunk
from app.services.embedder import GeminiEmbedder


def _to_chunk(item: Any) -> Chunk:
    """Convert a query result or dictionary into a canonical Chunk dataclass."""
    if isinstance(item, Chunk):
        return item

    if isinstance(item, dict):
        chunk_id = item.get("id", "")
        text = item.get("text", "")
        meta = item.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        start_s = item.get("start_s", meta.get("start_s", meta.get("start", 0.0)))
        end_s = item.get("end_s", meta.get("end_s", meta.get("end", start_s)))
        return Chunk(
            id=str(chunk_id),
            text=str(text),
            start_s=float(start_s),
            end_s=float(end_s),
        )

    chunk_id = getattr(item, "id", "")
    text = getattr(item, "text", "")
    meta = getattr(item, "metadata", None)
    if not isinstance(meta, dict):
        meta = {}

    start_s = getattr(item, "start_s", None)
    if start_s is None:
        start_s = meta.get("start_s", meta.get("start", 0.0))

    end_s = getattr(item, "end_s", None)
    if end_s is None:
        end_s = meta.get("end_s", meta.get("end", start_s))

    return Chunk(
        id=str(chunk_id),
        text=str(text),
        start_s=float(start_s),
        end_s=float(end_s),
    )


async def retrieve_chunks(
    store: VectorStore,
    embedder: GeminiEmbedder,
    video_id: str,
    query: str,
    top_k: int = 8,
    dedup_window_s: float = 10.0,
) -> list[Chunk]:
    """Retrieve, deduplicate, and chronologically sort transcript chunks for a query.

    Workflow:
    1. Embed query using `await embedder.embed_query(query)` (or `embed_batch([query])[0]`).
    2. Query `store.query(collection_name=video_id, query_embedding=query_embedding,
       top_k=top_k * 2)`.
    3. Deduplicate overlapping chunks: if multiple returned chunks have `start_s`
       within `dedup_window_s` of an already selected higher-scoring chunk, skip the duplicate.
    4. Truncate to at most `top_k`.
    5. Re-sort chronologically: sort the selected chunks by `start_s` ascending.
    6. Return list of Chunk dataclass instances.
    """
    if top_k <= 0:
        return []

    # 1. Embed query
    if hasattr(embedder, "embed_query"):
        emb_res = embedder.embed_query(query)
    else:
        emb_res = embedder.embed_batch([query])

    if inspect.isawaitable(emb_res):
        raw_embedding = await emb_res
    else:
        raw_embedding = emb_res

    if hasattr(embedder, "embed_query"):
        query_embedding: list[float] = raw_embedding  # type: ignore[assignment]
    else:
        query_embedding = raw_embedding[0] if raw_embedding else []

    # 2. Query vector store for candidates (top_k * 2 to allow dedup)
    fetch_k = top_k * 2
    query_coro = store.query(
        collection_name=video_id,
        query_embedding=query_embedding,
        top_k=fetch_k,
    )
    if inspect.isawaitable(query_coro):
        raw_results = await query_coro
    else:
        raw_results = query_coro

    if not raw_results:
        return []

    # 3. Deduplicate overlapping chunks
    # Results are returned in order of relevance (highest score first)
    selected: list[Chunk] = []
    for item in raw_results:
        chunk = _to_chunk(item)

        is_duplicate = False
        for s in selected:
            # Same ID is always duplicate
            if chunk.id == s.id:
                is_duplicate = True
                break
            # Overlapping start_s within dedup window
            if dedup_window_s > 0 and abs(chunk.start_s - s.start_s) <= dedup_window_s:
                is_duplicate = True
                break
            elif dedup_window_s == 0 and chunk.start_s == s.start_s:
                is_duplicate = True
                break

        if not is_duplicate:
            selected.append(chunk)
            # 4. Truncate to at most top_k
            if len(selected) >= top_k:
                break

    # 5. Re-sort chronologically: sort selected chunks by start_s ascending
    selected.sort(key=lambda c: (c.start_s, c.end_s))

    # 6. Return list[Chunk]
    return selected


__all__ = ["Chunk", "QueryResult", "VectorStore", "retrieve_chunks"]
