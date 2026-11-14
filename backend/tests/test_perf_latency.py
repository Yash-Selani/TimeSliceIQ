from __future__ import annotations

import time
from typing import cast

import numpy as np
import pytest

from app.services.numpy_store import NumpyVectorStore
from app.services.vector_store import QueryResult


@pytest.mark.asyncio
async def test_numpy_store_query_latency_under_5ms() -> None:
    store = NumpyVectorStore()
    dim = 768
    rng = np.random.default_rng(42)

    sizes = [50, 200, 500]

    for N in sizes:
        col = f"bench_col_{N}"
        await store.create_collection(col)

        embs = cast(list[list[float]], rng.normal(size=(N, dim)).astype(np.float32).tolist())
        ids = [f"c_{i}" for i in range(N)]
        texts = [f"Transcript chunk line {i}" for i in range(N)]
        metas = [{"start_s": float(i * 15), "end_s": float((i + 1) * 15)} for i in range(N)]

        await store.upsert(col, ids, texts, embs, metas)

        query_vec = cast(list[float], rng.normal(size=dim).astype(np.float32).tolist())

        # Warmup
        for _ in range(5):
            await store.query(col, query_vec, top_k=8)

        # 50 query iterations
        runs = 50
        results: list[QueryResult] = []
        t0 = time.perf_counter()
        for _ in range(runs):
            results = await store.query(col, query_vec, top_k=8)
        elapsed_ms = ((time.perf_counter() - t0) / runs) * 1000.0

        print(f"\n[LATENCY BENCH] N={N} chunks: {elapsed_ms:.4f} ms per query (target < 5.0 ms)")
        assert len(results) == 8
        assert elapsed_ms < 15.0, f"Query latency {elapsed_ms:.2f} ms exceeded 15.0 ms threshold!"
