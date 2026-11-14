from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class QueryResult:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float


@runtime_checkable
class VectorStore(Protocol):
    async def create_collection(self, name: str) -> None: ...

    async def has_collection(self, name: str) -> bool: ...

    async def upsert(
        self,
        collection_name: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

    async def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> list[QueryResult]: ...


def get_vector_store(backend: str = "numpy") -> VectorStore:
    """Factory function to instantiate a VectorStore backend.

    Supported backends:
      - "numpy": Pure Python + NumPy in-memory store.
      - "chroma": ChromaDB-backed vector store (requires chromadb).
    """
    backend_lower = backend.lower().strip()
    if backend_lower == "numpy":
        from app.services.numpy_store import NumpyVectorStore

        return NumpyVectorStore()
    elif backend_lower == "chroma":
        from app.services.chroma_store import ChromaVectorStore

        return ChromaVectorStore()
    else:
        raise ValueError(
            f"Unknown vector store backend: {backend!r}. Supported backends: 'numpy', 'chroma'."
        )


__all__ = ["QueryResult", "VectorStore", "get_vector_store"]
