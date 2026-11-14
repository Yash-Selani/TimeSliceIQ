from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.chunker import Chunk
from app.services.retriever import _to_chunk, retrieve_chunks
from app.services.vector_store import QueryResult, VectorStore


@pytest.fixture
def mock_embedder() -> AsyncMock:
    embedder = AsyncMock()
    embedder.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return embedder


@pytest.fixture
def mock_store() -> AsyncMock:
    store = AsyncMock(spec=VectorStore)
    return store


@pytest.mark.asyncio
async def test_retrieve_chunks_empty_results(
    mock_store: AsyncMock, mock_embedder: AsyncMock
) -> None:
    """Test when store returns no results, retrieve_chunks returns empty list."""
    mock_store.query.return_value = []

    result = await retrieve_chunks(
        store=mock_store,
        embedder=mock_embedder,
        video_id="video123",
        query="what is quantum computing?",
        top_k=5,
    )

    assert result == []
    mock_embedder.embed_query.assert_awaited_once_with("what is quantum computing?")
    mock_store.query.assert_awaited_once_with(
        collection_name="video123",
        query_embedding=[0.1, 0.2, 0.3],
        top_k=10,  # top_k * 2
    )


@pytest.mark.asyncio
async def test_retrieve_chunks_deduplication(
    mock_store: AsyncMock, mock_embedder: AsyncMock
) -> None:
    """Test deduplication logic skips chunks within dedup_window_s of higher-scoring chunks."""
    # Given:
    # c0: score 0.95, start 10.0 (selected)
    # c1: score 0.90, start 15.0 (within 10s of c0 -> duplicate, skipped)
    # c2: score 0.85, start 40.0 (selected)
    # c3: score 0.80, start 45.0 (within 10s of c2 -> duplicate, skipped)
    # c4: score 0.70, start 12.0 (within 10s of c0 -> duplicate, skipped)
    # c5: score 0.60, start 80.0 (selected)
    results = [
        QueryResult(
            id="c0",
            text="Intro part 1",
            metadata={"start_s": 10.0, "end_s": 25.0},
            score=0.95,
        ),
        QueryResult(
            id="c1",
            text="Intro part 2",
            metadata={"start_s": 15.0, "end_s": 30.0},
            score=0.90,
        ),
        QueryResult(
            id="c2",
            text="Middle part",
            metadata={"start_s": 40.0, "end_s": 55.0},
            score=0.85,
        ),
        QueryResult(
            id="c3",
            text="Middle part overlap",
            metadata={"start_s": 45.0, "end_s": 60.0},
            score=0.80,
        ),
        QueryResult(
            id="c4",
            text="Intro overlap 3",
            metadata={"start_s": 12.0, "end_s": 27.0},
            score=0.70,
        ),
        QueryResult(
            id="c5",
            text="Conclusion",
            metadata={"start_s": 80.0, "end_s": 95.0},
            score=0.60,
        ),
    ]
    mock_store.query.return_value = results

    chunks = await retrieve_chunks(
        store=mock_store,
        embedder=mock_embedder,
        video_id="vid_test",
        query="test query",
        top_k=8,
        dedup_window_s=10.0,
    )

    # c0, c2, c5 should be selected
    assert len(chunks) == 3
    assert [c.id for c in chunks] == ["c0", "c2", "c5"]
    assert [c.start_s for c in chunks] == [10.0, 40.0, 80.0]


@pytest.mark.asyncio
async def test_retrieve_chunks_chronological_resorting(
    mock_store: AsyncMock, mock_embedder: AsyncMock
) -> None:
    """Test that selected chunks are re-sorted by start_s ascending."""
    # c3 has highest score, starts at 200s
    # c1 has second score, starts at 50s
    # c2 has third score, starts at 120s
    results = [
        QueryResult(
            id="c3",
            text="Section 3",
            metadata={"start_s": 200.0, "end_s": 260.0},
            score=0.99,
        ),
        QueryResult(
            id="c1",
            text="Section 1",
            metadata={"start_s": 50.0, "end_s": 110.0},
            score=0.88,
        ),
        QueryResult(
            id="c2",
            text="Section 2",
            metadata={"start_s": 120.0, "end_s": 180.0},
            score=0.77,
        ),
    ]
    mock_store.query.return_value = results

    chunks = await retrieve_chunks(
        store=mock_store,
        embedder=mock_embedder,
        video_id="vid_order",
        query="ordering test",
        top_k=5,
        dedup_window_s=10.0,
    )

    assert len(chunks) == 3
    # Chronologically sorted: 50.0, 120.0, 200.0
    assert chunks[0].id == "c1"
    assert chunks[0].start_s == 50.0
    assert chunks[1].id == "c2"
    assert chunks[1].start_s == 120.0
    assert chunks[2].id == "c3"
    assert chunks[2].start_s == 200.0


@pytest.mark.asyncio
async def test_retrieve_chunks_top_k_truncation(
    mock_store: AsyncMock, mock_embedder: AsyncMock
) -> None:
    """Test truncation to top_k after deduplication."""
    # 6 distinct, non-overlapping chunks
    results = [
        QueryResult(
            id=f"c{i}",
            text=f"Text {i}",
            metadata={"start_s": i * 50.0, "end_s": i * 50.0 + 30.0},
            score=1.0 - (i * 0.1),
        )
        for i in range(6)
    ]
    mock_store.query.return_value = results

    chunks = await retrieve_chunks(
        store=mock_store,
        embedder=mock_embedder,
        video_id="vid_trunc",
        query="truncation test",
        top_k=3,
        dedup_window_s=10.0,
    )

    assert len(chunks) == 3
    # Top 3 scoring chunks were c0, c1, c2, chronologically ordered
    assert [c.id for c in chunks] == ["c0", "c1", "c2"]


@pytest.mark.asyncio
async def test_retrieve_chunks_duplicate_id_handling(
    mock_store: AsyncMock, mock_embedder: AsyncMock
) -> None:
    """Test that duplicate chunk IDs are not selected twice even if dedup_window_s is 0."""
    results = [
        QueryResult(
            id="c0",
            text="A",
            metadata={"start_s": 10.0, "end_s": 20.0},
            score=0.9,
        ),
        QueryResult(
            id="c0",
            text="A duplicate",
            metadata={"start_s": 50.0, "end_s": 60.0},
            score=0.8,
        ),
    ]
    mock_store.query.return_value = results

    chunks = await retrieve_chunks(
        store=mock_store,
        embedder=mock_embedder,
        video_id="vid_dup_id",
        query="dup id",
        top_k=5,
        dedup_window_s=0.0,
    )

    assert len(chunks) == 1
    assert chunks[0].id == "c0"


@pytest.mark.asyncio
async def test_retrieve_chunks_top_k_zero_or_negative(
    mock_store: AsyncMock, mock_embedder: AsyncMock
) -> None:
    """Test that top_k <= 0 returns empty list without calling store or embedder."""
    assert await retrieve_chunks(mock_store, mock_embedder, "v1", "query", top_k=0) == []
    assert await retrieve_chunks(mock_store, mock_embedder, "v1", "query", top_k=-2) == []
    mock_embedder.embed_query.assert_not_called()
    mock_store.query.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_chunks_fallback_embed_batch(
    mock_store: AsyncMock,
) -> None:
    """Test embedder without embed_query falls back to embed_batch."""

    class BatchOnlyEmbedder:
        def __init__(self) -> None:
            self.call_count = 0

        async def embed_batch(
            self, texts: list[str], batch_size: int = 100
        ) -> list[list[float]]:
            self.call_count += 1
            return [[0.5, 0.6, 0.7]]

    embedder = BatchOnlyEmbedder()
    mock_store.query.return_value = [
        QueryResult(
            id="c1",
            text="Sample",
            metadata={"start_s": 0.0, "end_s": 10.0},
            score=0.9,
        )
    ]

    chunks = await retrieve_chunks(
        store=mock_store,
        embedder=embedder,  # type: ignore[arg-type]
        video_id="vid_batch",
        query="batch fallback",
        top_k=2,
    )

    assert embedder.call_count == 1
    assert len(chunks) == 1
    assert chunks[0].id == "c1"


def test_to_chunk_helper_various_types() -> None:
    """Test _to_chunk helper on Chunk, QueryResult, dict, and fallback objects."""
    # Chunk instance
    c = Chunk(id="c1", text="hello", start_s=5.0, end_s=15.0)
    assert _to_chunk(c) is c

    # QueryResult with metadata
    qr = QueryResult(
        id="c2",
        text="world",
        metadata={"start_s": 20.0, "end_s": 30.0},
        score=0.8,
    )
    converted_qr = _to_chunk(qr)
    assert converted_qr.id == "c2"
    assert converted_qr.text == "world"
    assert converted_qr.start_s == 20.0
    assert converted_qr.end_s == 30.0

    # Dict
    d = {"id": "c3", "text": "dict chunk", "start_s": 1.0, "end_s": 2.0}
    converted_d = _to_chunk(d)
    assert converted_d.id == "c3"
    assert converted_d.start_s == 1.0
    assert converted_d.end_s == 2.0

    # Dict with nested metadata and alternate key 'start'
    d_meta = {
        "id": "c4",
        "text": "nested",
        "metadata": {"start": 100.5, "end": 120.0},
    }
    converted_d_meta = _to_chunk(d_meta)
    assert converted_d_meta.id == "c4"
    assert converted_d_meta.start_s == 100.5
    assert converted_d_meta.end_s == 120.0
