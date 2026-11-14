from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_chunker,
    get_embedder,
    get_metadata_service,
    get_transcript_fetcher,
    get_vector_store,
)
from app.main import create_app
from app.schemas import ErrorCode
from app.services.chunker import Chunk
from app.services.metadata import VideoMetadata
from app.services.transcript import (
    NoCaptionsError,
    TranscriptBlockedError,
    VideoUnavailableError,
)
from app.services.vector_store import VectorStore


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_ingest_success(test_app, client):
    # Mock services
    mock_metadata = AsyncMock(
        return_value=VideoMetadata(title="Test Video Title", channel="Test Channel")
    )
    raw_snippets = [
        {"start": 0.0, "duration": 5.0, "text": "Hello world"},
        {"start": 5.0, "duration": 7.0, "text": "Welcome to the test"},
        {"start": 12.0, "duration": 4.0, "text": "Final part of intro"},
    ]
    mock_transcript = AsyncMock(return_value=raw_snippets)

    chunks = [
        Chunk(id="c0", text="Hello world Welcome to the test", start_s=0.0, end_s=12.0),
        Chunk(id="c1", text="Welcome to the test Final part of intro", start_s=5.0, end_s=16.0),
    ]
    mock_chunker = MagicMock(return_value=chunks)

    mock_embedder = MagicMock()
    mock_embedder.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

    mock_store = MagicMock(spec=VectorStore)
    mock_store.create_collection = AsyncMock()
    mock_store.upsert = AsyncMock()

    test_app.dependency_overrides[get_metadata_service] = lambda: mock_metadata
    test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
    test_app.dependency_overrides[get_chunker] = lambda: mock_chunker
    test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
    test_app.dependency_overrides[get_vector_store] = lambda: mock_store

    response = client.post(
        "/api/ingest",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "dQw4w9WgXcQ"
    assert data["title"] == "Test Video Title"
    assert data["channel"] == "Test Channel"
    assert data["duration_s"] == 16
    assert data["chunk_count"] == 2
    assert len(data["transcript"]) >= 1

    mock_store.create_collection.assert_awaited_once_with("dQw4w9WgXcQ")
    mock_store.upsert.assert_awaited_once()
    mock_embedder.embed_batch.assert_awaited_once_with(
        ["Hello world Welcome to the test", "Welcome to the test Final part of intro"]
    )


def test_ingest_short_url_and_alt_route(test_app, client):
    mock_metadata = AsyncMock(
        return_value=VideoMetadata(title="Short URL Title", channel="Creator")
    )
    mock_transcript = AsyncMock(
        return_value=[{"start": 0.0, "duration": 10.0, "text": "Short clip"}]
    )
    mock_chunker = MagicMock(
        return_value=[Chunk(id="c0", text="Short clip", start_s=0.0, end_s=10.0)]
    )
    mock_embedder = MagicMock()
    mock_embedder.embed_batch = AsyncMock(return_value=[[0.5, 0.5]])
    mock_store = MagicMock(spec=VectorStore)
    mock_store.create_collection = AsyncMock()
    mock_store.upsert = AsyncMock()

    test_app.dependency_overrides[get_metadata_service] = lambda: mock_metadata
    test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
    test_app.dependency_overrides[get_chunker] = lambda: mock_chunker
    test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
    test_app.dependency_overrides[get_vector_store] = lambda: mock_store

    # Test /ingest without /api prefix
    response = client.post(
        "/ingest",
        json={"url": "https://youtu.be/dQw4w9WgXcQ?t=10"},
    )
    assert response.status_code == 200
    assert response.json()["video_id"] == "dQw4w9WgXcQ"


def test_ingest_invalid_url(client):
    response = client.post(
        "/api/ingest",
        json={"url": "https://vimeo.com/12345678"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == ErrorCode.INVALID_URL.value
    assert "valid YouTube link" in data["message"]


def test_ingest_malformed_body(client):
    response = client.post("/api/ingest", json={"invalid_field": 123})
    assert response.status_code == 422


def test_ingest_no_captions_error(test_app, client):
    mock_transcript = AsyncMock(side_effect=NoCaptionsError("No captions found"))
    test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript

    response = client.post(
        "/api/ingest",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == ErrorCode.NO_CAPTIONS.value
    assert "captions" in data["message"]


def test_ingest_video_unavailable_error(test_app, client):
    mock_transcript = AsyncMock(side_effect=VideoUnavailableError("Private video"))
    test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript

    response = client.post(
        "/api/ingest",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == ErrorCode.VIDEO_UNAVAILABLE.value
    assert "unavailable" in data["message"]


def test_ingest_transcript_blocked_error(test_app, client):
    mock_transcript = AsyncMock(side_effect=TranscriptBlockedError("IP blocked by YouTube"))
    test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript

    response = client.post(
        "/api/ingest",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 502
    data = response.json()
    assert data["code"] == ErrorCode.TRANSCRIPT_BLOCKED.value
    assert "blocked" in data["message"]
