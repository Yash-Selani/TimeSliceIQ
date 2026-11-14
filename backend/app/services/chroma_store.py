from __future__ import annotations

from typing import Any

from app.services.vector_store import QueryResult, VectorStore


class ChromaVectorStore:
    """ChromaDB implementation of the VectorStore protocol.

    Wraps chromadb.EphemeralClient() if chromadb is available.
    If chromadb is not installed, raises RuntimeError or gracefully falls back to NumpyVectorStore.
    """

    def __init__(
        self,
        client: Any = None,
        fallback_to_numpy: bool = False,
    ) -> None:
        if client is not None:
            self._client = client
            self._fallback: VectorStore | None = None
            return

        try:
            import chromadb

            self._client = chromadb.EphemeralClient()
            self._fallback = None
        except ImportError:
            if fallback_to_numpy:
                from app.services.numpy_store import NumpyVectorStore

                self._fallback = NumpyVectorStore()
                self._client = None
            else:
                raise RuntimeError("ChromaDB is not installed, use NumpyVectorStore") from None

    async def create_collection(self, name: str) -> None:
        if self._fallback is not None:
            await self._fallback.create_collection(name)
            return

        self._client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    async def has_collection(self, name: str) -> bool:
        if self._fallback is not None:
            return await self._fallback.has_collection(name)

        try:
            self._client.get_collection(name=name)
            return True
        except Exception:
            return False

    async def upsert(
        self,
        collection_name: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if self._fallback is not None:
            await self._fallback.upsert(collection_name, ids, texts, embeddings, metadatas)
            return

        if not ids:
            return

        collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    async def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> list[QueryResult]:
        if self._fallback is not None:
            return await self._fallback.query(collection_name, query_embedding, top_k)

        if top_k <= 0:
            return []

        try:
            collection = self._client.get_collection(name=collection_name)
        except Exception:
            return []

        count = collection.count()
        if count == 0:
            return []

        k = min(top_k, count)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        res_ids = results["ids"][0]
        res_docs = (
            results.get("documents", [[]])[0] if results.get("documents") else [""] * len(res_ids)
        )
        res_metas = (
            results.get("metadatas", [[]])[0] if results.get("metadatas") else [{}] * len(res_ids)
        )
        res_dists = (
            results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(res_ids)
        )

        query_results: list[QueryResult] = []
        for id_, doc, meta, dist in zip(res_ids, res_docs, res_metas, res_dists):
            # In ChromaDB with cosine space, distance = 1 - cosine_similarity
            score = 1.0 - float(dist) if dist is not None else 0.0
            query_results.append(
                QueryResult(
                    id=str(id_),
                    text=str(doc) if doc is not None else "",
                    metadata=dict(meta) if isinstance(meta, dict) else {},
                    score=score,
                )
            )
        return query_results


__all__ = ["ChromaVectorStore"]
