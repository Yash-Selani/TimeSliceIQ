"""Export OpenAPI spec with all schema models included.

Creates a temporary FastAPI app with dummy routes that reference every
request/response model so they appear in the generated OpenAPI JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    IngestRequest,
    IngestResponse,
)


def build_spec_app() -> FastAPI:
    app = FastAPI(
        title="TimeSliceIQ API",
        version="0.1.0",
        description="Ask questions about YouTube videos with timestamped citations.",
    )

    @app.post(
        "/api/ingest",
        response_model=IngestResponse,
        responses={
            422: {"model": ErrorResponse},
        },
        tags=["ingest"],
        summary="Ingest a YouTube video",
    )
    async def ingest(body: IngestRequest) -> IngestResponse:  # noqa: ARG001
        ...

    @app.post(
        "/api/chat",
        response_model=ChatResponse,
        responses={
            422: {"model": ErrorResponse},
        },
        tags=["chat"],
        summary="Chat about an ingested video",
    )
    async def chat(body: ChatRequest) -> ChatResponse:  # noqa: ARG001
        ...

    return app


def main() -> None:
    app = build_spec_app()
    spec = app.openapi()
    out = Path(__file__).resolve().parent.parent.parent / "openapi.json"
    out.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"OpenAPI spec written to {out}")


if __name__ == "__main__":
    main()
