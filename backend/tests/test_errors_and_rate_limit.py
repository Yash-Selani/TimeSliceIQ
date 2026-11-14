from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.errors import (
    RateLimitError,
    invalid_url_handler,
    llm_failed_handler,
    no_captions_handler,
    rate_limited_handler,
    register_error_handlers,
    transcript_blocked_handler,
    validation_exception_handler,
    video_unavailable_handler,
)
from app.main import SlidingWindowRateLimiter, create_app
from app.schemas import ErrorCode
from app.services.synthesizer import LLMFailedError
from app.services.transcript import (
    NoCaptionsError,
    TranscriptBlockedError,
    VideoUnavailableError,
)
from app.services.url_parser import InvalidURLError


def test_rate_limiter_allows_and_blocks():
    app = create_app()
    # Configure tiny rate limit for test
    limiter = SlidingWindowRateLimiter(requests_per_minute=3, window_seconds=60.0)
    app.state.rate_limiter = limiter

    # Update middleware limiter
    for middleware in app.user_middleware:
        if hasattr(middleware, "kwargs") and "limiter" in middleware.kwargs:
            middleware.kwargs["limiter"] = limiter

    # Rebuild middleware stack by creating TestClient
    client = TestClient(app)

    # Health check is exempt from rate limit
    for _ in range(5):
        res = client.get("/health")
        assert res.status_code == 200

    # Preflight OPTIONS with CORS headers is exempt from rate limit
    for _ in range(5):
        res = client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert res.status_code == 200

    # API endpoints are tracked: requests with same client IP
    # First 3 should pass
    res1 = client.post("/api/chat", json={})
    res2 = client.post("/api/chat", json={})
    res3 = client.post("/api/chat", json={})
    assert res1.status_code == 422  # Handled by route validation
    assert res2.status_code == 422
    assert res3.status_code == 422

    # 4th request should be blocked with 429
    res4 = client.post("/api/chat", json={})
    assert res4.status_code == 429
    data = res4.json()
    assert data["code"] == ErrorCode.RATE_LIMITED.value
    assert "Too many requests" in data["message"]

    # Reset limiter allows requests again
    limiter.reset()
    res5 = client.post("/api/chat", json={})
    assert res5.status_code == 422


def test_cors_middleware():
    app = create_app()
    client = TestClient(app)

    # Preflight OPTIONS request
    res = client.options(
        "/api/ingest",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:5173")

    # Regular GET /health request has CORS headers
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:5173")


@pytest.mark.asyncio
async def test_all_error_handlers_directly():
    dummy_req = None  # Handlers only use status/content

    # InvalidURLError -> 400
    res = await invalid_url_handler(dummy_req, InvalidURLError("Bad URL"))
    assert res.status_code == 400
    assert ErrorCode.INVALID_URL.value in res.body.decode()

    # NoCaptionsError -> 404
    res = await no_captions_handler(dummy_req, NoCaptionsError("No captions"))
    assert res.status_code == 404
    assert ErrorCode.NO_CAPTIONS.value in res.body.decode()

    # VideoUnavailableError -> 404
    res = await video_unavailable_handler(dummy_req, VideoUnavailableError("Private"))
    assert res.status_code == 404
    assert ErrorCode.VIDEO_UNAVAILABLE.value in res.body.decode()

    # TranscriptBlockedError -> 502
    res = await transcript_blocked_handler(dummy_req, TranscriptBlockedError("Blocked"))
    assert res.status_code == 502
    assert ErrorCode.TRANSCRIPT_BLOCKED.value in res.body.decode()

    # LLMFailedError -> 502
    res = await llm_failed_handler(dummy_req, LLMFailedError("Quota exceeded"))
    assert res.status_code == 502
    assert ErrorCode.LLM_FAILED.value in res.body.decode()

    # RateLimitError -> 429
    res = await rate_limited_handler(dummy_req, RateLimitError("Rate limited"))
    assert res.status_code == 429
    assert ErrorCode.RATE_LIMITED.value in res.body.decode()

    # RequestValidationError -> 422
    val_exc = RequestValidationError(
        errors=[{"loc": ("body", "url"), "msg": "field required", "type": "missing"}]
    )
    res = await validation_exception_handler(dummy_req, val_exc)
    assert res.status_code == 422
    assert "field required" in res.body.decode()


def test_register_error_handlers_adds_handlers():
    app = FastAPI()
    register_error_handlers(app)
    assert InvalidURLError in app.exception_handlers
    assert NoCaptionsError in app.exception_handlers
    assert VideoUnavailableError in app.exception_handlers
    assert TranscriptBlockedError in app.exception_handlers
    assert LLMFailedError in app.exception_handlers
    assert RateLimitError in app.exception_handlers
    assert RequestValidationError in app.exception_handlers
