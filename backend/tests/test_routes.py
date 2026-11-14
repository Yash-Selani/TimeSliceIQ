from __future__ import annotations

import asyncio
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_chunker,
    get_embedder,
    get_metadata_service,
    get_synthesizer,
    get_transcript_fetcher,
    get_vector_store,
)
from app.main import SlidingWindowRateLimiter, create_app
from app.schemas import (
    ERROR_MESSAGES,
    AnswerBlock,
    ChatMessage,
    ChatResponse,
    Citation,
    ErrorCode,
    ErrorResponse,
    IngestResponse,
)
from app.services.chunker import Chunk, chunk_transcript
from app.services.metadata import VideoMetadata
from app.services.numpy_store import NumpyVectorStore
from app.services.synthesizer import LLMFailedError, Synthesizer
from app.services.transcript import (
    NoCaptionsError,
    TranscriptBlockedError,
    VideoUnavailableError,
)

# ---------------------------------------------------------------------------
# Test Fixtures & Sample Data
# ---------------------------------------------------------------------------

SAMPLE_VIDEO_ID = "dQw4w9WgXcQ"
SAMPLE_URL = f"https://www.youtube.com/watch?v={SAMPLE_VIDEO_ID}"

SAMPLE_RAW_TRANSCRIPT = [
    {"start": 0.0, "duration": 4.5, "text": "Welcome to neural networks."},
    {"start": 4.5, "duration": 5.0, "text": "Today we cover backprop and gradient descent."},
    {"start": 9.5, "duration": 6.0, "text": "Examine the chain rule for derivatives."},
    {"start": 15.5, "duration": 5.5, "text": "Next observe how weights are updated."},
    {"start": 21.0, "duration": 7.0, "text": "Discuss convergence and learning rate."},
]


@pytest.fixture
def test_app():
    """Create a clean FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
def client(test_app):
    """TestClient bound to the test FastAPI app."""
    return TestClient(test_app)


def _validate_schema_fields(
    payload: dict[str, Any],
    schema_name: str,
    spec: dict[str, Any],
) -> None:
    """Helper to validate payload against OpenAPI schema required fields and types."""
    schemas = spec.get("components", {}).get("schemas", {})
    assert schema_name in schemas, f"Schema '{schema_name}' missing from OpenAPI spec components"
    schema_def = schemas[schema_name]

    required_fields = schema_def.get("required", [])
    for field in required_fields:
        assert field in payload, (
            f"Required field '{field}' for schema '{schema_name}' missing from payload"
        )

    properties = schema_def.get("properties", {})
    for key, val in payload.items():
        if key in properties:
            prop = properties[key]
            prop_type = prop.get("type")
            if prop_type == "string":
                assert isinstance(val, str), f"Field '{key}' expected string, got {type(val)}"
            elif prop_type == "integer":
                assert isinstance(val, int) and not isinstance(val, bool), (
                    f"Field '{key}' expected int, got {type(val)}"
                )
            elif prop_type == "number":
                assert isinstance(val, int | float) and not isinstance(val, bool), (
                    f"Field '{key}' expected number, got {type(val)}"
                )
            elif prop_type == "array":
                assert isinstance(val, list), f"Field '{key}' expected array, got {type(val)}"
            elif prop_type == "object":
                assert isinstance(val, dict), f"Field '{key}' expected object, got {type(val)}"
            elif prop_type == "boolean":
                assert isinstance(val, bool), f"Field '{key}' expected bool, got {type(val)}"


# ---------------------------------------------------------------------------
# 1. Full Ingest Flow (POST /api/ingest)
# ---------------------------------------------------------------------------


class TestIngestFlow:
    """Tests full ingest flow with mocked external services."""

    def test_ingest_success(self, test_app, client):
        mock_metadata = AsyncMock(
            return_value=VideoMetadata(
                title="Neural Networks Explained",
                channel="AI Academy",
            )
        )
        mock_transcript = AsyncMock(return_value=SAMPLE_RAW_TRANSCRIPT)

        store = NumpyVectorStore()
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(
            side_effect=lambda texts, **kw: [[0.05 * (i + 1)] * 8 for i in range(len(texts))]
        )

        test_app.dependency_overrides[get_metadata_service] = lambda: mock_metadata
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
        test_app.dependency_overrides[get_chunker] = lambda: chunk_transcript
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_vector_store] = lambda: store

        response = client.post("/api/ingest", json={"url": SAMPLE_URL})

        assert response.status_code == 200
        data = response.json()

        # Validate response conforms to IngestResponse Pydantic model
        validated = IngestResponse.model_validate(data)
        assert validated.video_id == SAMPLE_VIDEO_ID
        assert validated.title == "Neural Networks Explained"
        assert validated.channel == "AI Academy"
        assert validated.duration_s == 28
        assert validated.chunk_count > 0
        assert len(validated.transcript) > 0

        # Validate transcript grouping (~10-15s windows with start_s and text)
        for line in validated.transcript:
            assert line.start_s >= 0.0
            assert len(line.text.strip()) > 0

        # Verify underlying vector store has indexed the collection
        assert asyncio.run(store.has_collection(SAMPLE_VIDEO_ID))
        mock_metadata.assert_awaited_once_with(SAMPLE_VIDEO_ID)
        mock_transcript.assert_awaited_once()
        mock_embedder.embed_batch.assert_awaited_once()

    def test_ingest_short_url_and_unprefixed_alias(self, test_app, client):
        mock_metadata = AsyncMock(
            return_value=VideoMetadata(title="Short URL Clip", channel="QuickTips")
        )
        mock_transcript = AsyncMock(
            return_value=[{"start": 0.0, "duration": 10.0, "text": "Quick intro"}]
        )
        store = NumpyVectorStore()
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(return_value=[[0.1] * 8])

        test_app.dependency_overrides[get_metadata_service] = lambda: mock_metadata
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
        test_app.dependency_overrides[get_chunker] = lambda: chunk_transcript
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_vector_store] = lambda: store

        # Test both short URL format and the unprefixed /ingest alias
        response = client.post("/ingest", json={"url": f"https://youtu.be/{SAMPLE_VIDEO_ID}?t=5"})
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == SAMPLE_VIDEO_ID
        assert data["title"] == "Short URL Clip"


# ---------------------------------------------------------------------------
# 2. Full Chat Flow (POST /api/chat) on Ingested Video
# ---------------------------------------------------------------------------


class TestChatFlow:
    """Tests chat flow on an already indexed video with retrieval and citations."""

    def test_chat_full_flow_on_ingested_video(self, test_app, client):
        store = NumpyVectorStore()

        # Pre-seed vector store as if video was previously ingested
        chunks = [
            Chunk(
                id="c0",
                text="Welcome to neural networks deep dive. We cover backprop.",
                start_s=0.0,
                end_s=9.5,
            ),
            Chunk(
                id="c1",
                text="First, examine the chain rule for partial derivatives.",
                start_s=9.5,
                end_s=15.5,
            ),
            Chunk(
                id="c2",
                text="Next, observe how weights are updated via gradient descent.",
                start_s=15.5,
                end_s=28.0,
            ),
        ]

        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(
            return_value=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        mock_embedder.embed_query = AsyncMock(return_value=[0.0, 1.0, 0.0])

        asyncio.run(store.create_collection(SAMPLE_VIDEO_ID))
        asyncio.run(
            store.upsert(
                collection_name=SAMPLE_VIDEO_ID,
                ids=[c.id for c in chunks],
                texts=[c.text for c in chunks],
                embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                metadatas=[{"start_s": c.start_s, "end_s": c.end_s} for c in chunks],
            )
        )

        expected_response = ChatResponse(
            blocks=[
                AnswerBlock(
                    text="The video explains the chain rule for calculating partial derivatives.",
                    cites=[Citation(chunk_id="c1", label="00:09", seconds=9.5)],
                ),
                AnswerBlock(
                    text="It then discusses gradient descent for weight updates.",
                    cites=[Citation(chunk_id="c2", label="00:15", seconds=15.5)],
                ),
            ],
            follow_ups=[
                "How does the learning rate affect convergence?",
                "What is backpropagation?",
            ],
        )

        mock_synthesizer = MagicMock(spec=Synthesizer)
        mock_synthesizer.synthesize = AsyncMock(return_value=expected_response)

        test_app.dependency_overrides[get_vector_store] = lambda: store
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

        response = client.post(
            "/api/chat",
            json={
                "video_id": SAMPLE_VIDEO_ID,
                "question": "What mathematical concepts are discussed?",
                "history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello! Ask me anything about this video."},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Validate with Pydantic model
        validated = ChatResponse.model_validate(data)
        assert len(validated.blocks) == 2
        assert len(validated.follow_ups) == 2

        # Verify citation validation:
        # Check chunk_id format, timestamp bounds, and human-readable label
        for block in validated.blocks:
            assert len(block.text) > 0
            for cite in block.cites:
                assert cite.chunk_id in ("c0", "c1", "c2")
                assert cite.seconds >= 0.0
                assert re.match(r"^\d{2}:\d{2}(:\d{2})?$", cite.label)

        # Verify synthesizer was called with retrieved chunks and history
        assert mock_synthesizer.synthesize.await_count == 1
        call_kwargs = mock_synthesizer.synthesize.await_args.kwargs
        assert call_kwargs["question"] == "What mathematical concepts are discussed?"
        assert len(call_kwargs["chunks"]) > 0
        assert len(call_kwargs["history"]) == 2
        assert isinstance(call_kwargs["history"][0], ChatMessage)


# ---------------------------------------------------------------------------
# 3. Cold Start Resilience (ensure_indexed)
# ---------------------------------------------------------------------------


class TestColdStartResilience:
    """Verify ensure_indexed automatically re-ingests when chat arrives for an unindexed video."""

    def test_cold_start_automatic_indexing(self, test_app, client):
        store = NumpyVectorStore()  # Completely empty store

        mock_transcript_fetcher = AsyncMock(return_value=SAMPLE_RAW_TRANSCRIPT)
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(
            side_effect=lambda texts, **kw: [[0.1] * 8 for _ in texts]
        )
        mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 8)

        mock_synthesizer = MagicMock(spec=Synthesizer)
        mock_synthesizer.synthesize = AsyncMock(
            return_value=ChatResponse(
                blocks=[AnswerBlock(text="Answer generated after cold start indexing.", cites=[])],
                follow_ups=["Follow up 1"],
            )
        )

        test_app.dependency_overrides[get_vector_store] = lambda: store
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript_fetcher
        test_app.dependency_overrides[get_chunker] = lambda: chunk_transcript
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

        # First chat request on an unindexed video triggers cold start indexing
        response1 = client.post(
            "/api/chat",
            json={"video_id": SAMPLE_VIDEO_ID, "question": "What is covered in this video?"},
        )

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["blocks"][0]["text"] == "Answer generated after cold start indexing."

        # Verify transcript fetcher and embed_batch were invoked to populate the index
        assert mock_transcript_fetcher.await_count == 1
        assert mock_embedder.embed_batch.await_count == 1

        # Second chat request on the now indexed video MUST NOT re-index
        response2 = client.post(
            "/api/chat",
            json={"video_id": SAMPLE_VIDEO_ID, "question": "Tell me more about backprop."},
        )

        assert response2.status_code == 200
        # Transcript fetcher and embed_batch count remains 1 (idempotent / cached)
        assert mock_transcript_fetcher.await_count == 1
        assert mock_embedder.embed_batch.await_count == 1


# ---------------------------------------------------------------------------
# 4. Error Path Integration
# ---------------------------------------------------------------------------


class TestErrorPathIntegration:
    """Tests all required error response codes and payloads."""

    def test_error_invalid_url_400(self, client):
        """INVALID_URL returns 400 Bad Request."""
        invalid_urls = [
            "https://vimeo.com/12345678",
            "not-a-url",
            "https://youtube.com/watch?v=short",  # Not 11 chars
            "https://dailymotion.com/video/x7tgad0",
        ]
        for url in invalid_urls:
            response = client.post("/api/ingest", json={"url": url})
            assert response.status_code == 400
            data = response.json()
            err = ErrorResponse.model_validate(data)
            assert err.code == ErrorCode.INVALID_URL
            assert err.message == ERROR_MESSAGES[ErrorCode.INVALID_URL]

    def test_error_no_captions_404(self, test_app, client):
        """NO_CAPTIONS returns 404 Not Found."""
        mock_transcript = AsyncMock(side_effect=NoCaptionsError("No transcripts found"))
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript

        # On ingest
        res_ingest = client.post("/api/ingest", json={"url": SAMPLE_URL})
        assert res_ingest.status_code == 404
        data = res_ingest.json()
        err = ErrorResponse.model_validate(data)
        assert err.code == ErrorCode.NO_CAPTIONS
        assert err.message == ERROR_MESSAGES[ErrorCode.NO_CAPTIONS]

        # On cold start chat
        test_app.dependency_overrides[get_vector_store] = lambda: NumpyVectorStore()
        res_chat = client.post(
            "/api/chat",
            json={"video_id": SAMPLE_VIDEO_ID, "question": "Hello?"},
        )
        assert res_chat.status_code == 404
        err_chat = ErrorResponse.model_validate(res_chat.json())
        assert err_chat.code == ErrorCode.NO_CAPTIONS

    def test_error_video_unavailable_404(self, test_app, client):
        """VIDEO_UNAVAILABLE returns 404 Not Found."""
        mock_transcript = AsyncMock(side_effect=VideoUnavailableError("Video is private"))
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript

        response = client.post("/api/ingest", json={"url": SAMPLE_URL})
        assert response.status_code == 404
        data = response.json()
        err = ErrorResponse.model_validate(data)
        assert err.code == ErrorCode.VIDEO_UNAVAILABLE
        assert err.message == ERROR_MESSAGES[ErrorCode.VIDEO_UNAVAILABLE]

    def test_error_transcript_blocked_502(self, test_app, client):
        """TRANSCRIPT_BLOCKED returns 502 Bad Gateway."""
        mock_transcript = AsyncMock(
            side_effect=TranscriptBlockedError("Too Many Requests / IP blocked")
        )
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript

        response = client.post("/api/ingest", json={"url": SAMPLE_URL})
        assert response.status_code == 502
        data = response.json()
        err = ErrorResponse.model_validate(data)
        assert err.code == ErrorCode.TRANSCRIPT_BLOCKED
        assert err.message == ERROR_MESSAGES[ErrorCode.TRANSCRIPT_BLOCKED]

    def test_error_llm_failed_502(self, test_app, client):
        """LLM_FAILED returns 502 Bad Gateway."""
        store = NumpyVectorStore()
        asyncio.run(store.create_collection(SAMPLE_VIDEO_ID))
        mock_embedder = MagicMock()
        mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 8)

        # Synthesizer fails due to Gemini API timeout or parsing error
        mock_synthesizer = MagicMock(spec=Synthesizer)
        mock_synthesizer.synthesize = AsyncMock(
            side_effect=LLMFailedError("Gemini quota exhausted or invalid JSON")
        )

        test_app.dependency_overrides[get_vector_store] = lambda: store
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

        response = client.post(
            "/api/chat",
            json={"video_id": SAMPLE_VIDEO_ID, "question": "What is backprop?"},
        )
        assert response.status_code == 502
        data = response.json()
        err = ErrorResponse.model_validate(data)
        assert err.code == ErrorCode.LLM_FAILED
        assert err.message == ERROR_MESSAGES[ErrorCode.LLM_FAILED]

    def test_error_rate_limited_429(self):
        """RATE_LIMITED returns 429 Too Many Requests when request quota is exceeded."""
        app = create_app()
        # Set quota to 2 requests per 60 seconds
        limiter = SlidingWindowRateLimiter(requests_per_minute=2, window_seconds=60.0)
        app.state.rate_limiter = limiter

        for middleware in app.user_middleware:
            if hasattr(middleware, "kwargs") and "limiter" in middleware.kwargs:
                middleware.kwargs["limiter"] = limiter

        custom_client = TestClient(app)

        # First 2 requests pass through to route validation (422)
        res1 = custom_client.post("/api/chat", json={})
        res2 = custom_client.post("/api/chat", json={})
        assert res1.status_code == 422
        assert res2.status_code == 422

        # 3rd request is blocked by RateLimitMiddleware with 429
        res3 = custom_client.post("/api/chat", json={})
        assert res3.status_code == 429
        err = ErrorResponse.model_validate(res3.json())
        assert err.code == ErrorCode.RATE_LIMITED
        assert err.message == ERROR_MESSAGES[ErrorCode.RATE_LIMITED]

        # Resetting limiter allows calls again
        limiter.reset()
        res4 = custom_client.post("/api/chat", json={})
        assert res4.status_code == 422

    def test_rate_limiter_exemptions(self):
        """Health check and preflight OPTIONS requests are exempt from rate limiting."""
        app = create_app()
        limiter = SlidingWindowRateLimiter(requests_per_minute=1, window_seconds=60.0)
        app.state.rate_limiter = limiter

        for middleware in app.user_middleware:
            if hasattr(middleware, "kwargs") and "limiter" in middleware.kwargs:
                middleware.kwargs["limiter"] = limiter

        custom_client = TestClient(app)

        # Health endpoint can be called repeatedly without getting 429
        for _ in range(5):
            res = custom_client.get("/health")
            assert res.status_code == 200

        # OPTIONS preflight can be called repeatedly without getting 429
        for _ in range(5):
            res = custom_client.options(
                "/api/chat",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "POST",
                },
            )
            assert res.status_code == 200


# ---------------------------------------------------------------------------
# 5. CORS Headers Verification
# ---------------------------------------------------------------------------


class TestCorsHeaders:
    """Verifies CORS headers on preflight OPTIONS and response headers."""

    def test_cors_preflight_options_ingest(self, client):
        response = client.options(
            "/api/ingest",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers
        assert headers["access-control-allow-origin"] in ("*", "http://localhost:5173")
        assert "access-control-allow-methods" in headers
        allowed_methods = headers["access-control-allow-methods"].upper()
        assert "POST" in allowed_methods or "*" in allowed_methods

    def test_cors_preflight_options_chat(self, client):
        response = client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        assert response.status_code == 200
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers
        assert headers["access-control-allow-origin"] in ("*", "http://localhost:3000")

    def test_cors_headers_on_api_responses(self, test_app, client):
        mock_metadata = AsyncMock(return_value=VideoMetadata(title="Title", channel="Channel"))
        mock_transcript = AsyncMock(return_value=SAMPLE_RAW_TRANSCRIPT)
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(return_value=[[0.1] * 8])

        test_app.dependency_overrides[get_metadata_service] = lambda: mock_metadata
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
        test_app.dependency_overrides[get_chunker] = lambda: chunk_transcript
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_vector_store] = lambda: NumpyVectorStore()

        # Check CORS header on successful POST /api/ingest
        res = client.post(
            "/api/ingest",
            json={"url": SAMPLE_URL},
            headers={"Origin": "http://localhost:5173"},
        )
        assert res.status_code == 200
        res_headers = {k.lower(): v for k, v in res.headers.items()}
        assert "access-control-allow-origin" in res_headers

        # Check CORS header on GET /health
        res_health = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert res_health.status_code == 200
        health_headers = {k.lower(): v for k, v in res_health.headers.items()}
        assert "access-control-allow-origin" in health_headers


# ---------------------------------------------------------------------------
# 6. OpenAPI Schema Compliance of Responses
# ---------------------------------------------------------------------------


class TestOpenApiSchemaCompliance:
    """Verifies that endpoint responses strictly conform to the OpenAPI 3.1 schema specification."""

    def test_openapi_spec_endpoints_and_components(self, test_app, client):
        spec = test_app.openapi()
        assert spec["openapi"].startswith("3.")
        assert spec["info"]["title"] == "TimeSliceIQ API"

        # Check paths exist
        assert "/api/ingest" in spec["paths"]
        assert "post" in spec["paths"]["/api/ingest"]
        assert "/api/chat" in spec["paths"]
        assert "post" in spec["paths"]["/api/chat"]

        # Check component schemas
        schemas = spec["components"]["schemas"]
        expected_schemas = [
            "IngestRequest",
            "IngestResponse",
            "TranscriptLine",
            "ChatRequest",
            "ChatMessage",
            "ChatResponse",
            "AnswerBlock",
            "Citation",
            "ErrorCode",
            "ErrorResponse",
        ]
        for s in expected_schemas:
            assert s in schemas, f"OpenAPI components missing schema: {s}"

        # Fetch via HTTP endpoint
        res = client.get("/openapi.json")
        assert res.status_code == 200
        http_spec = res.json()
        assert http_spec["info"]["title"] == "TimeSliceIQ API"

    def test_ingest_response_conforms_to_openapi_schema(self, test_app, client):
        spec = test_app.openapi()

        mock_meta = VideoMetadata(title="Test Title", channel="Test Author")
        mock_metadata = AsyncMock(return_value=mock_meta)
        mock_transcript = AsyncMock(return_value=SAMPLE_RAW_TRANSCRIPT)
        mock_embedder = MagicMock()
        mock_embedder.embed_batch = AsyncMock(return_value=[[0.1] * 8])

        test_app.dependency_overrides[get_metadata_service] = lambda: mock_metadata
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
        test_app.dependency_overrides[get_chunker] = lambda: chunk_transcript
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_vector_store] = lambda: NumpyVectorStore()

        response = client.post("/api/ingest", json={"url": SAMPLE_URL})
        assert response.status_code == 200
        payload = response.json()

        # Validate against OpenAPI specification definition
        _validate_schema_fields(payload, "IngestResponse", spec)

        # Validate nested transcript lines against TranscriptLine schema
        for line in payload["transcript"]:
            _validate_schema_fields(line, "TranscriptLine", spec)

    def test_chat_response_conforms_to_openapi_schema(self, test_app, client):
        spec = test_app.openapi()

        store = NumpyVectorStore()
        asyncio.run(store.create_collection(SAMPLE_VIDEO_ID))
        mock_embedder = MagicMock()
        mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 8)

        mock_synthesizer = MagicMock(spec=Synthesizer)
        mock_synthesizer.synthesize = AsyncMock(
            return_value=ChatResponse(
                blocks=[
                    AnswerBlock(
                        text="Here is the grounded answer.",
                        cites=[Citation(chunk_id="c0", label="00:05", seconds=5.0)],
                    )
                ],
                follow_ups=["Follow up query 1", "Follow up query 2"],
            )
        )

        test_app.dependency_overrides[get_vector_store] = lambda: store
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

        response = client.post(
            "/api/chat",
            json={"video_id": SAMPLE_VIDEO_ID, "question": "Explain this clip."},
        )
        assert response.status_code == 200
        payload = response.json()

        # Validate against ChatResponse schema
        _validate_schema_fields(payload, "ChatResponse", spec)

        # Validate nested blocks and citations
        for block in payload["blocks"]:
            _validate_schema_fields(block, "AnswerBlock", spec)
            for cite in block["cites"]:
                _validate_schema_fields(cite, "Citation", spec)

    def test_error_responses_conform_to_openapi_schema(self, test_app, client):
        spec = client.app.openapi()

        # 400 Invalid URL
        res_400 = client.post("/api/ingest", json={"url": "bad-url"})
        assert res_400.status_code == 400
        _validate_schema_fields(res_400.json(), "ErrorResponse", spec)

        # 404 No Captions
        mock_transcript = AsyncMock(side_effect=NoCaptionsError("No captions"))
        test_app.dependency_overrides[get_transcript_fetcher] = lambda: mock_transcript
        res_404 = client.post("/api/ingest", json={"url": SAMPLE_URL})
        assert res_404.status_code == 404
        _validate_schema_fields(res_404.json(), "ErrorResponse", spec)

        # 502 LLM Failed
        store = NumpyVectorStore()
        asyncio.run(store.create_collection(SAMPLE_VIDEO_ID))
        mock_embedder = MagicMock()
        mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 8)
        mock_synthesizer = MagicMock(spec=Synthesizer)
        mock_synthesizer.synthesize = AsyncMock(side_effect=LLMFailedError("Error"))

        test_app.dependency_overrides[get_vector_store] = lambda: store
        test_app.dependency_overrides[get_embedder] = lambda: mock_embedder
        test_app.dependency_overrides[get_synthesizer] = lambda: mock_synthesizer

        res_502 = client.post(
            "/api/chat",
            json={"video_id": SAMPLE_VIDEO_ID, "question": "Question?"},
        )
        assert res_502.status_code == 502
        _validate_schema_fields(res_502.json(), "ErrorResponse", spec)
