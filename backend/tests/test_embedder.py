from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import tenacity
from google.genai import types

from app.services.embedder import DEFAULT_MODEL, GeminiEmbedder


def _make_mock_response(embeddings_data: list[list[float]]) -> types.EmbedContentResponse:
    return types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=vals) for vals in embeddings_data]
    )


def test_init_with_client() -> None:
    mock_client = MagicMock()
    embedder = GeminiEmbedder(model="custom-model", client=mock_client)
    assert embedder.client is mock_client
    assert embedder.model == "custom-model"


@patch("app.services.embedder.genai.Client")
def test_init_with_api_key(mock_client_cls: MagicMock) -> None:
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    embedder = GeminiEmbedder(api_key="custom_api_key")
    assert embedder.client is mock_instance
    assert embedder.model == DEFAULT_MODEL
    mock_client_cls.assert_called_once_with(api_key="custom_api_key")


@patch("app.services.embedder.genai.Client")
def test_init_with_gemini_env_key(
    mock_client_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env_gemini_key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    embedder = GeminiEmbedder()
    assert embedder.client is mock_instance
    mock_client_cls.assert_called_once_with(api_key="env_gemini_key")


@patch("app.services.embedder.genai.Client")
def test_init_with_google_env_key(
    mock_client_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "env_google_key")
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    embedder = GeminiEmbedder()
    assert embedder.client is mock_instance
    mock_client_cls.assert_called_once_with(api_key="env_google_key")


@patch("app.services.embedder.genai.Client")
def test_init_without_env_or_key(
    mock_client_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    embedder = GeminiEmbedder()
    assert embedder.client is mock_instance
    mock_client_cls.assert_called_once_with()


@pytest.mark.asyncio
async def test_embed_batch_empty() -> None:
    mock_client = MagicMock()
    embedder = GeminiEmbedder(client=mock_client)

    result = await embedder.embed_batch([])
    assert result == []
    mock_client.models.embed_content.assert_not_called()


@pytest.mark.asyncio
async def test_embed_batch_single_chunk() -> None:
    mock_client = MagicMock()
    expected = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.models.embed_content.return_value = _make_mock_response(expected)

    embedder = GeminiEmbedder(client=mock_client)
    texts = ["hello world", "gemini embeddings"]
    result = await embedder.embed_batch(texts)

    assert result == expected
    mock_client.models.embed_content.assert_called_once_with(
        model=DEFAULT_MODEL,
        contents=texts,
    )


@pytest.mark.asyncio
async def test_embed_batch_chunking_250_texts() -> None:
    """Verify 250 texts split into batches of 100, 100, and 50."""
    mock_client = MagicMock()
    total_texts = 250
    texts = [f"text chunk {i}" for i in range(total_texts)]

    def side_effect(model: str, contents: list[str]) -> types.EmbedContentResponse:
        return _make_mock_response([[float(len(t))] for t in contents])

    mock_client.models.embed_content.side_effect = side_effect

    embedder = GeminiEmbedder(client=mock_client)
    result = await embedder.embed_batch(texts, batch_size=100)

    assert len(result) == 250
    assert mock_client.models.embed_content.call_count == 3

    calls = mock_client.models.embed_content.call_args_list
    assert len(calls[0].kwargs["contents"]) == 100
    assert calls[0].kwargs["contents"] == texts[0:100]

    assert len(calls[1].kwargs["contents"]) == 100
    assert calls[1].kwargs["contents"] == texts[100:200]

    assert len(calls[2].kwargs["contents"]) == 50
    assert calls[2].kwargs["contents"] == texts[200:250]


@pytest.mark.asyncio
async def test_embed_batch_custom_batch_size() -> None:
    mock_client = MagicMock()
    texts = ["a", "b", "c", "d", "e"]

    def side_effect(model: str, contents: list[str]) -> types.EmbedContentResponse:
        return _make_mock_response([[1.0] for _ in contents])

    mock_client.models.embed_content.side_effect = side_effect

    embedder = GeminiEmbedder(client=mock_client)
    result = await embedder.embed_batch(texts, batch_size=2)

    assert len(result) == 5
    assert mock_client.models.embed_content.call_count == 3

    calls = mock_client.models.embed_content.call_args_list
    assert calls[0].kwargs["contents"] == ["a", "b"]
    assert calls[1].kwargs["contents"] == ["c", "d"]
    assert calls[2].kwargs["contents"] == ["e"]


@pytest.mark.asyncio
async def test_embed_batch_invalid_batch_size() -> None:
    mock_client = MagicMock()
    embedder = GeminiEmbedder(client=mock_client)

    with pytest.raises(ValueError, match="batch_size must be positive"):
        await embedder.embed_batch(["text"], batch_size=0)

    with pytest.raises(ValueError, match="batch_size must be positive"):
        await embedder.embed_batch(["text"], batch_size=-5)


@pytest.mark.asyncio
async def test_embed_batch_none_embeddings() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = None
    mock_client.models.embed_content.return_value = mock_response

    embedder = GeminiEmbedder(client=mock_client)
    result = await embedder.embed_batch(["text"])
    assert result == []


@pytest.mark.asyncio
async def test_embed_batch_dict_and_list_embeddings() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = [
        {"values": [0.1, 0.2]},
        [0.3, 0.4],
    ]
    mock_client.models.embed_content.return_value = mock_response

    embedder = GeminiEmbedder(client=mock_client)
    result = await embedder.embed_batch(["text 1", "text 2"])
    assert result == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_retry_on_temporary_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    expected = [[0.9, 0.8]]
    success_response = _make_mock_response(expected)

    mock_client.models.embed_content.side_effect = [
        RuntimeError("Temporary 503 Service Unavailable"),
        success_response,
    ]

    embedder = GeminiEmbedder(client=mock_client)
    monkeypatch.setattr(embedder._embed_batch_sync.retry, "wait", tenacity.wait_none())

    result = await embedder.embed_batch(["retry test"])
    assert result == expected
    assert mock_client.models.embed_content.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError("Fatal API Error")

    embedder = GeminiEmbedder(client=mock_client)
    monkeypatch.setattr(embedder._embed_batch_sync.retry, "wait", tenacity.wait_none())

    with pytest.raises(RuntimeError, match="Fatal API Error"):
        await embedder.embed_batch(["fail test"])

    assert mock_client.models.embed_content.call_count == 3


@pytest.mark.asyncio
async def test_embed_query_success() -> None:
    mock_client = MagicMock()
    expected = [0.11, 0.22, 0.33]
    mock_client.models.embed_content.return_value = _make_mock_response([expected])

    embedder = GeminiEmbedder(client=mock_client)
    result = await embedder.embed_query("search question")

    assert result == expected
    mock_client.models.embed_content.assert_called_once_with(
        model=DEFAULT_MODEL,
        contents=["search question"],
    )


@pytest.mark.asyncio
async def test_embed_query_empty_response() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = None
    mock_client.models.embed_content.return_value = mock_response

    embedder = GeminiEmbedder(client=mock_client)
    result = await embedder.embed_query("empty test")
    assert result == []
