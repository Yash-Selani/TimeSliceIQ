from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_chunker,
    get_embedder,
    get_synthesizer,
    get_transcript_fetcher,
    get_vector_store,
)
from app.main import create_app
from app.schemas import AnswerBlock, ChatResponse, Citation, ErrorCode
from app.services.chunker import Chunk
from app.services.synthesizer import LLMFailedError, Synthesizer
from app.services.vector_store import VectorStore


@pytest.fixture
def test_app():
    return create_app()


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_chat_success_already_indexed(test_app, client):
    mock_store = MagicMock(spec=VectorStore)
    mock_store.has_collection = AsyncMock(return_value=True)
    # Return mock QueryResult objects
    mock_query_result = MagicMock()
    mock_query_result.id = "c0"
    mock_query_result.text = "Grounded text from video"
    mock_query_result.metadata = {"start_s": 10.0, "end_s": 25.0}
    mock_store.query = AsyncMock(return_value=[mock_query_result])

    mock_embedder = MagicMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

    expected_response = ChatResponse(
        blocks=[
            AnswerBlock(
                text="The video discusses key algorithms.",
                cites=[Citation(chunk_id="c0", label="00:10", seconds=10.0)],
            )
        ],
        follow_ups=["What about complexity?"],
    )
    mock_synthesizer = MagicMock(spec=Synthesizer)
    mock_synthesizer.synthesize = AsyncMock(return_value=expected_response)

    test_app.dependency_overrides[get_vector_store] = lambda: mock_store
    test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
    test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

    response = client.post(
        "/api/chat",
        json={
            "video_id": "dQw4w9WgXcQ",
            "question": "What is this video about?",
            "history": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["blocks"]) == 1
    assert data["blocks"][0]["text"] == "The video discusses key algorithms."
    assert data["blocks"][0]["cites"][0]["chunk_id"] == "c0"
    assert data["blocks"][0]["cites"][0]["label"] == "00:10"
    assert data["follow_ups"] == ["What about complexity?"]

    # has_collection was called; store.create_collection was NOT called because it was indexed
    mock_store.has_collection.assert_awaited_once_with("dQw4w9WgXcQ")
    mock_store.create_collection.assert_not_called()


def test_chat_cold_start_reindexing(test_app, client):
    """When collection is not in vector store, ensure_indexed triggers auto-reindexing."""
    mock_store = MagicMock(spec=VectorStore)
    mock_store.has_collection = AsyncMock(return_value=False)
    mock_store.create_collection = AsyncMock()
    mock_store.upsert = AsyncMock()
    mock_store.query = AsyncMock(return_value=[])

    mock_transcript_fetcher = AsyncMock(
        return_value=[{"start": 0.0, "duration": 15.0, "text": "Cold start speech"}]
    )
    mock_chunker = MagicMock(
        return_value=[Chunk(id="c0", text="Cold start speech", start_s=0.0, end_s=15.0)]
    )
    mock_embedder = MagicMock()
    mock_embedder.embed_batch = AsyncMock(return_value=[[0.1, 0.2]])
    mock_embedder.embed_query = AsyncMock(return_value=[0.1, 0.2])

    mock_synthesizer = MagicMock(spec=Synthesizer)
    mock_synthesizer.synthesize = AsyncMock(
        return_value=ChatResponse(
            blocks=[AnswerBlock(text="Answer after re-index", cites=[])],
            follow_ups=[],
        )
    )

    test_app.dependency_overrides[get_vector_store] = lambda: mock_store
    test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript_fetcher
    test_app.dependency_overrides[get_chunker] = lambda: mock_chunker
    test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
    test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

    response = client.post(
        "/chat",
        json={
            "video_id": "dQw4w9WgXcQ",
            "question": "Explain after restart",
            "history": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["blocks"][0]["text"] == "Answer after re-index"

    # Verify reindexing occurred
    mock_store.create_collection.assert_awaited_once_with("dQw4w9WgXcQ")
    mock_store.upsert.assert_awaited_once()


def test_chat_llm_failed_error(test_app, client):
    mock_store = MagicMock(spec=VectorStore)
    mock_store.has_collection = AsyncMock(return_value=True)
    mock_store.query = AsyncMock(return_value=[])

    mock_embedder = MagicMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1, 0.2])

    mock_synthesizer = MagicMock(spec=Synthesizer)
    mock_synthesizer.synthesize = AsyncMock(
        side_effect=LLMFailedError("Gemini quota exhausted")
    )

    test_app.dependency_overrides[get_vector_store] = lambda: mock_store
    test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
    test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

    response = client.post(
        "/api/chat",
        json={
            "video_id": "dQw4w9WgXcQ",
            "question": "What is AI?",
        },
    )

    assert response.status_code == 502
    data = response.json()
    assert data["code"] == ErrorCode.LLM_FAILED.value
    assert "couldn't process" in data["message"]


def test_chat_validation_error(client):
    # Missing required question field
    response = client.post(
        "/api/chat",
        json={"video_id": "dQw4w9WgXcQ"},
    )
    assert response.status_code == 422
