from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.errors import register_error_handlers
from app.routes.chat import router as chat_router
from app.routes.ingest import router as ingest_router
from app.schemas import ERROR_MESSAGES, ErrorCode, ErrorResponse


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter per client IP."""

    def __init__(self, requests_per_minute: int = 60, window_seconds: float = 60.0) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.history: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            # Prune timestamps older than window
            timestamps = [t for t in self.history[client_ip] if t > cutoff]
            if len(timestamps) >= self.requests_per_minute:
                self.history[client_ip] = timestamps
                return False
            timestamps.append(now)
            self.history[client_ip] = timestamps
            return True

    def reset(self) -> None:
        """Clear rate limit history (primarily for tests)."""
        self.history.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware enforcing per-IP rate limits."""

    def __init__(self, app: FastAPI, limiter: SlidingWindowRateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip OPTIONS (CORS preflight) and docs/health endpoints
        if request.method == "OPTIONS" or request.url.path in (
            "/",
            "/health",
            "/api/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ):
            return await call_next(request)

        # Extract client IP (checking X-Forwarded-For if behind reverse proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client and request.client.host:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        if not await self.limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    code=ErrorCode.RATE_LIMITED,
                    message=ERROR_MESSAGES[ErrorCode.RATE_LIMITED],
                ).model_dump(),
            )

        return await call_next(request)


def create_app() -> FastAPI:
    """Create and configure the TimeSliceIQ FastAPI application."""
    app = FastAPI(
        title="TimeSliceIQ API",
        version="0.1.0",
        description="Ask questions about YouTube videos with timestamped citations.",
    )

    # 1. Register domain & validation exception handlers
    register_error_handlers(app)

    # 2. Include API routes
    app.include_router(ingest_router)
    app.include_router(chat_router)

    # 3. Health check endpoint
    @app.get("/health", tags=["health"])
    @app.get("/api/health", tags=["health"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # 4. Attach rate limiter
    limiter = SlidingWindowRateLimiter(
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    )
    app.state.rate_limiter = limiter

    # Add middlewares (order: last added is outermost)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
