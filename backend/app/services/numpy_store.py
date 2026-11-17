from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from app.services.vector_store import QueryResult

logger = logging.getLogger(__name__)


def _get_cache_dir() -> Path:
    cache_dir = Path(tempfile.gettempdir()) / "timesliceiq_cache"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return cache_dir


class NumpyVectorStore:
    """Pure Python + NumPy in-memory vector store with /tmp disk caching."""

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, Any]] = {}
        self._cache_dir = _get_cache_dir()

    def _get_cache_path(self, name: str) -> Path:
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
        return self._cache_dir / f"col_{safe_name}.npz"

    def _try_load_cache(self, name: str) -> bool:
        cache_path = self._get_cache_path(name)
        if not cache_path.exists():
            return False
        try:
            with np.load(cache_path, allow_pickle=True) as data:
                ids = list(data["ids"])
                texts = list(data["texts"])
                embeddings = data["embeddings"]
                raw_meta = str(data["metadatas"])
                metadatas = json.loads(raw_meta)
                self._collections[name] = {
                    "ids": ids,
                    "texts": texts,
                    "embeddings": embeddings,
                    "metadatas": metadatas,
                }
                return True
        except Exception as exc:
            logger.debug("Failed to load vector cache from %s: %s", cache_path, exc)
            return False

    def _save_cache(self, name: str) -> None:
        if name not in self._collections:
            return
        coll = self._collections[name]
        cache_path = self._get_cache_path(name)
        try:
            np.savez_compressed(
                cache_path,
                ids=np.array(coll["ids"], dtype=object),
                texts=np.array(coll["texts"], dtype=object),
                embeddings=coll["embeddings"],
                metadatas=json.dumps(coll["metadatas"]),
            )
        except Exception as exc:
            logger.debug("Failed to persist vector cache to %s: %s", cache_path, exc)

    async def create_collection(self, name: str) -> None:
        if name in self._collections:
            return
        if self._try_load_cache(name):
            return
        self._collections[name] = {
            "ids": [],
            "texts": [],
            "embeddings": np.empty((0, 0), dtype=np.float32),
            "metadatas": [],
        }

    async def has_collection(self, name: str) -> bool:
        if name in self._collections:
            return True
        return self._try_load_cache(name)

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
            self._save_cache(collection_name)
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

        self._save_cache(collection_name)

    async def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> list[QueryResult]:
        if collection_name not in self._collections:
            self._try_load_cache(collection_name)

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
