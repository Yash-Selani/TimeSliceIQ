from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, TypeVar
from unittest.mock import MagicMock

import pytest

from app.services.chroma_store import ChromaVectorStore
from app.services.numpy_store import NumpyVectorStore
from app.services.vector_store import VectorStore, get_vector_store

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    """Synchronously advance a pure in-memory coroutine."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


def test_numpy_vector_store_protocol_compliance() -> None:
    store = NumpyVectorStore()
    assert isinstance(store, VectorStore)


def test_numpy_vector_store_collections() -> None:
    store = NumpyVectorStore()
    assert not run(store.has_collection("test_col"))

    run(store.create_collection("test_col"))
    assert run(store.has_collection("test_col"))

    # Creating again should be idempotent
    run(store.create_collection("test_col"))
    assert run(store.has_collection("test_col"))


def test_numpy_vector_store_upsert_and_query_closest() -> None:
    store = NumpyVectorStore()
    col_name = "test_col"

    ids = ["c0", "c1", "c2"]
    texts = ["machine learning intro", "cooking pasta recipe", "deep neural networks"]
    # 3D embeddings
    # c0: aligned with X axis
    # c1: aligned with Y axis
    # c2: aligned mostly with X axis, slightly Y
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.8, 0.2, 0.0],
    ]
    metadatas = [
        {"start_s": 0.0, "end_s": 60.0},
        {"start_s": 60.0, "end_s": 120.0},
        {"start_s": 120.0, "end_s": 180.0},
    ]

    run(store.upsert(col_name, ids, texts, embeddings, metadatas))

    # Query with vector identical to c0
    results = run(store.query(col_name, query_embedding=[1.0, 0.0, 0.0], top_k=2))

    assert len(results) == 2
    assert results[0].id == "c0"
    assert results[0].text == "machine learning intro"
    assert results[0].metadata["start_s"] == 0.0
    assert pytest.approx(results[0].score, abs=1e-4) == 1.0

    # Second result should be c2 (score ~0.97), not c1 (score ~0.0)
    assert results[1].id == "c2"
    assert results[1].score > 0.9


def test_numpy_vector_store_cosine_similarity_ordering() -> None:
    store = NumpyVectorStore()
    col_name = "ordering_col"

    ids = ["ortho", "same", "opposite"]
    texts = ["orthogonal", "same direction", "opposite direction"]
    embeddings = [
        [0.0, 1.0],   # Orthogonal to [1, 0] -> dot = 0
        [2.0, 0.0],   # Same direction as [1, 0] -> dot = 1
        [-1.0, 0.0],  # Opposite direction to [1, 0] -> dot = -1
    ]
    metadatas: list[dict[str, Any]] = [{}, {}, {}]

    run(store.upsert(col_name, ids, texts, embeddings, metadatas))

    results = run(store.query(col_name, query_embedding=[1.0, 0.0], top_k=3))

    assert len(results) == 3
    assert [r.id for r in results] == ["same", "ortho", "opposite"]
    assert pytest.approx(results[0].score, abs=1e-4) == 1.0
    assert pytest.approx(results[1].score, abs=1e-4) == 0.0
    assert pytest.approx(results[2].score, abs=1e-4) == -1.0


def test_numpy_vector_store_top_k_greater_than_collection_size() -> None:
    store = NumpyVectorStore()
    col_name = "small_col"

    ids = ["c0", "c1"]
    texts = ["text 0", "text 1"]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    metadatas: list[dict[str, Any]] = [{"idx": 0}, {"idx": 1}]

    run(store.upsert(col_name, ids, texts, embeddings, metadatas))

    # top_k=10 > 2 items
    results = run(store.query(col_name, query_embedding=[1.0, 0.0], top_k=10))
    assert len(results) == 2


def test_numpy_vector_store_upsert_update_existing_id() -> None:
    store = NumpyVectorStore()
    col_name = "update_col"

    # Initial insert
    run(
        store.upsert(
            col_name,
            ids=["c0", "c1"],
            texts=["initial c0", "initial c1"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            metadatas=[{"v": 1}, {"v": 1}],
        )
    )

    # Upsert with c0 updated and c2 added
    run(
        store.upsert(
            col_name,
            ids=["c0", "c2"],
            texts=["updated c0", "new c2"],
            embeddings=[[0.0, 1.0], [1.0, 1.0]],
            metadatas=[{"v": 2}, {"v": 1}],
        )
    )

    results = run(store.query(col_name, query_embedding=[0.0, 1.0], top_k=5))
    # Total distinct items should be 3: c0, c1, c2
    assert len(results) == 3

    c0_result = next(r for r in results if r.id == "c0")
    assert c0_result.text == "updated c0"
    assert c0_result.metadata["v"] == 2
    assert pytest.approx(c0_result.score, abs=1e-4) == 1.0


def test_numpy_vector_store_edge_cases() -> None:
    store = NumpyVectorStore()

    # Query non-existent collection
    res_non_existent = run(store.query("non_existent", [1.0, 0.0]))
    assert res_non_existent == []

    # Query empty collection
    run(store.create_collection("empty_col"))
    res_empty = run(store.query("empty_col", [1.0, 0.0]))
    assert res_empty == []

    # Query with top_k <= 0
    res_zero_k = run(store.query("empty_col", [1.0, 0.0], top_k=0))
    assert res_zero_k == []

    # Upsert with empty lists
    run(store.upsert("empty_col", [], [], [], []))
    assert len(run(store.query("empty_col", [1.0, 0.0]))) == 0

    # Upsert with mismatched lengths raises ValueError
    with pytest.raises(ValueError, match="same length"):
        run(store.upsert("empty_col", ["c0"], ["t0"], [[1.0]], []))


def test_chroma_vector_store_missing_dependency() -> None:
    # If chromadb is not installed, ChromaVectorStore() should raise RuntimeError
    try:
        import chromadb  # noqa: F401

        pytest.skip("chromadb is installed in this environment")
    except ImportError:
        with pytest.raises(RuntimeError, match="ChromaDB is not installed"):
            ChromaVectorStore(fallback_to_numpy=False)

        # But fallback_to_numpy=True should work smoothly
        fallback_store = ChromaVectorStore(fallback_to_numpy=True)
        assert isinstance(fallback_store, VectorStore)
        run(
            fallback_store.upsert(
                "fallback_col",
                ["c0"],
                ["fallback text"],
                [[1.0, 0.0]],
                [{"tag": "test"}],
            )
        )
        res = run(fallback_store.query("fallback_col", [1.0, 0.0], top_k=1))
        assert len(res) == 1
        assert res[0].id == "c0"
        assert res[0].text == "fallback text"


def test_chroma_vector_store_with_mock_client() -> None:
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_collection.return_value = mock_collection
    mock_client.get_or_create_collection.return_value = mock_collection

    store = ChromaVectorStore(client=mock_client)
    assert isinstance(store, VectorStore)

    # test create_collection
    run(store.create_collection("col_a"))
    mock_client.get_or_create_collection.assert_called_with(
        name="col_a", metadata={"hnsw:space": "cosine"}
    )

    # test has_collection
    assert run(store.has_collection("col_a"))
    mock_client.get_collection.side_effect = Exception("Not found")
    assert not run(store.has_collection("col_missing"))

    # test upsert
    mock_client.get_collection.side_effect = None
    mock_client.get_collection.return_value = mock_collection
    run(
        store.upsert(
            "col_a",
            ["c0"],
            ["mock text"],
            [[0.5, 0.5]],
            [{"start_s": 10.0}],
        )
    )
    mock_collection.upsert.assert_called_once_with(
        ids=["c0"],
        documents=["mock text"],
        embeddings=[[0.5, 0.5]],
        metadatas=[{"start_s": 10.0}],
    )

    # test query
    mock_collection.count.return_value = 1
    mock_collection.query.return_value = {
        "ids": [["c0"]],
        "documents": [["mock text"]],
        "metadatas": [[{"start_s": 10.0}]],
        "distances": [[0.1]],  # cosine distance = 0.1 -> score = 0.9
    }
    results = run(store.query("col_a", [0.5, 0.5], top_k=1))
    assert len(results) == 1
    assert results[0].id == "c0"
    assert results[0].text == "mock text"
    assert pytest.approx(results[0].score, abs=1e-4) == 0.9


def test_get_vector_store_factory() -> None:
    numpy_store = get_vector_store("numpy")
    assert isinstance(numpy_store, NumpyVectorStore)

    with pytest.raises(ValueError, match="Unknown vector store backend"):
        get_vector_store("unsupported_backend")
