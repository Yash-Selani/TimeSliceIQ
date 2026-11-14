from __future__ import annotations

from typing import Any

import numpy as np

from app.services.vector_store import QueryResult


class NumpyVectorStore:
    """Pure Python + NumPy in-memory vector store implementing the VectorStore protocol."""

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, Any]] = {}

    async def create_collection(self, name: str) -> None:
        if name not in self._collections:
            self._collections[name] = {
                "ids": [],
                "texts": [],
                "embeddings": np.empty((0, 0), dtype=np.float32),
                "metadatas": [],
            }

    async def has_collection(self, name: str) -> bool:
        return name in self._collections

    async def upsert(
        self,
        collection_name: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError(
                "ids, texts, embeddings, and metadatas must all have the same length"
            )

        if collection_name not in self._collections:
            await self.create_collection(collection_name)

        if not ids:
            return

        coll = self._collections[collection_name]
        existing_ids: list[str] = coll["ids"]
        existing_texts: list[str] = coll["texts"]
        existing_embeddings: np.ndarray = coll["embeddings"]
        existing_metadatas: list[dict[str, Any]] = coll["metadatas"]

        if not existing_ids:
            coll["ids"] = list(ids)
            coll["texts"] = list(texts)
            coll["embeddings"] = np.asarray(embeddings, dtype=np.float32)
            coll["metadatas"] = [dict(m) for m in metadatas]
            return

        id_to_idx = {id_: i for i, id_ in enumerate(existing_ids)}

        append_ids: list[str] = []
        append_texts: list[str] = []
        append_embeddings: list[list[float]] = []
        append_metadatas: list[dict[str, Any]] = []

        for id_, text, emb, meta in zip(ids, texts, embeddings, metadatas):
            if id_ in id_to_idx:
                idx = id_to_idx[id_]
                existing_texts[idx] = text
                existing_embeddings[idx] = np.asarray(emb, dtype=np.float32)
                existing_metadatas[idx] = dict(meta)
            else:
                id_to_idx[id_] = len(existing_ids) + len(append_ids)
                append_ids.append(id_)
                append_texts.append(text)
                append_embeddings.append(emb)
                append_metadatas.append(dict(meta))

        if append_ids:
            coll["ids"].extend(append_ids)
            coll["texts"].extend(append_texts)
            coll["metadatas"].extend(append_metadatas)
            new_arr = np.asarray(append_embeddings, dtype=np.float32)
            coll["embeddings"] = np.vstack([existing_embeddings, new_arr])

    async def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> list[QueryResult]:
        if collection_name not in self._collections or top_k <= 0:
            return []

        coll = self._collections[collection_name]
        n_items = len(coll["ids"])
        if n_items == 0:
            return []

        query_vec = np.asarray(query_embedding, dtype=np.float32)
        embeddings_mat = coll["embeddings"]

        # Cosine similarity: dot(A, B) / (norm(A) * norm(B) + 1e-9)
        dot_products = np.dot(embeddings_mat, query_vec)
        norm_embeddings = np.linalg.norm(embeddings_mat, axis=1)
        norm_query = np.linalg.norm(query_vec)
        scores = dot_products / (norm_embeddings * norm_query + 1e-9)

        k = min(top_k, n_items)
        top_indices = np.argsort(-scores)[:k]

        return [
            QueryResult(
                id=coll["ids"][idx],
                text=coll["texts"][idx],
                metadata=dict(coll["metadatas"][idx]),
                score=float(scores[idx]),
            )
            for idx in top_indices
        ]


__all__ = ["NumpyVectorStore"]
