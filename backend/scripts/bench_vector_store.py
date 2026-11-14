from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.services.numpy_store import NumpyVectorStore  # noqa: E402


async def run_benchmark():
    print("Initializing NumpyVectorStore benchmark...", flush=True)
    store = NumpyVectorStore()
    dim = 768
    rng = np.random.default_rng(42)

    # Typical chunk sizes: 50 chunks (15-min), 200 chunks (1-hour), 500 chunks (2.5-hour)
    sizes = [50, 200, 500]

    for N in sizes:
        col = f"col_{N}"
        await store.create_collection(col)

        # Generate embeddings directly as float32 list
        embs_arr = rng.normal(size=(N, dim)).astype(np.float32)
        embs = cast(list[list[float]], embs_arr.tolist())
        ids = [f"c_{i}" for i in range(N)]
        texts = [f"Transcript chunk line {i}" for i in range(N)]
        metas = [{"start_s": float(i * 15), "end_s": float((i + 1) * 15)} for i in range(N)]

        await store.upsert(col, ids, texts, embs, metas)

        query_vec = cast(list[float], rng.normal(size=dim).astype(np.float32).tolist())

        # Warmup
        for _ in range(5):
            await store.query(col, query_vec, top_k=8)

        # Benchmark 50 query runs
        iterations = 50
        t0 = time.perf_counter()
        for _ in range(iterations):
            _ = await store.query(col, query_vec, top_k=8)
        elapsed_total = time.perf_counter() - t0
        avg_ms = (elapsed_total / iterations) * 1000.0

        print(
            f"N = {N:4d} chunks | {dim} dims | Top-K: 8 | Avg: {avg_ms:6.3f} ms | Target: < 5ms",
            flush=True,
        )
        assert avg_ms < 5.0, f"Query latency {avg_ms:.2f}ms >= 5.0ms"

    print("All NumpyVectorStore latency benchmarks completed within < 5ms!", flush=True)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
