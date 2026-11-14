from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# On Windows in network-isolated sandboxes, socket.socketpair() blocks on 127.0.0.1.
# Patch ProactorEventLoop self-pipe so that asyncio runs cleanly without requiring network.
try:
    import asyncio.proactor_events
    import signal

    def _safe_make_self_pipe(self: Any) -> None:
        self._ssock = MagicMock()
        self._csock = MagicMock()
        self._csock.fileno.return_value = 1
        self._internal_fds = getattr(self, "_internal_fds", 0) + 1

    asyncio.proactor_events.BaseProactorEventLoop._make_self_pipe = _safe_make_self_pipe
    asyncio.proactor_events.BaseProactorEventLoop._close_self_pipe = lambda self: None
    asyncio.proactor_events.BaseProactorEventLoop._write_to_self = lambda self: None
    asyncio.proactor_events.BaseProactorEventLoop._loop_self_reading = lambda self, f=None: None
    signal.set_wakeup_fd = lambda *args, **kwargs: -1
except Exception:
    pass

from app.schemas import AnswerBlock, ChatMessage, ChatResponse, Citation
from app.services.chunker import Chunk
from app.services.prompt import GeminiAnswerBlock, GeminiResponseSchema
from app.services.synthesizer import (
    DEFAULT_MODEL,
    LLMFailedError,
    Synthesizer,
    seconds_to_label,
)

# ---------------------------------------------------------------------------
# seconds_to_label Tests
# ---------------------------------------------------------------------------


def test_seconds_to_label_under_one_hour() -> None:
    assert seconds_to_label(75.0) == "01:15"
    assert seconds_to_label(765.0) == "12:45"
    assert seconds_to_label(0.0) == "00:00"
    assert seconds_to_label(59.0) == "00:59"
    assert seconds_to_label(60.0) == "01:00"
    assert seconds_to_label(3599.0) == "59:59"


def test_seconds_to_label_one_hour_and_above() -> None:
    assert seconds_to_label(3600.0) == "01:00:00"
    assert seconds_to_label(3665.0) == "01:01:05"
    assert seconds_to_label(7325.0) == "02:02:05"
    assert seconds_to_label(36000.0) == "10:00:00"


def test_seconds_to_label_edge_cases() -> None:
    assert seconds_to_label(75.9) == "01:15"
    assert seconds_to_label(-5.0) == "00:00"


# ---------------------------------------------------------------------------
# Synthesizer Initialization Tests
# ---------------------------------------------------------------------------


def test_init_with_client() -> None:
    mock_client = MagicMock()
    synth = Synthesizer(model="gemini-custom", client=mock_client)
    assert synth.client is mock_client
    assert synth.model == "gemini-custom"


@patch("app.services.synthesizer.genai.Client")
def test_init_with_api_key(mock_client_cls: MagicMock) -> None:
    mock_inst = MagicMock()
    mock_client_cls.return_value = mock_inst

    synth = Synthesizer(api_key="test_api_key")
    assert synth.client is mock_inst
    assert synth.model == DEFAULT_MODEL
    mock_client_cls.assert_called_once_with(api_key="test_api_key")


@patch("app.services.synthesizer.genai.Client")
def test_init_with_env_key(
    mock_client_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env_secret")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    mock_inst = MagicMock()
    mock_client_cls.return_value = mock_inst

    synth = Synthesizer()
    assert synth.client is mock_inst
    mock_client_cls.assert_called_once_with(api_key="env_secret")


# ---------------------------------------------------------------------------
# Synthesize Async Method Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk(id="c0", text="Introductory remarks and overview.", start_s=75.0, end_s=120.0),
        Chunk(id="c1", text="Deep dive into attention mechanisms.", start_s=765.0, end_s=840.0),
        Chunk(id="c2", text="Conclusion and future work.", start_s=3665.0, end_s=3720.0),
    ]


@pytest.mark.asyncio
async def test_empty_chunks_returns_not_covered() -> None:
    synth = Synthesizer(client=MagicMock())
    result = await synth.synthesize(question="What is this about?", chunks=[])

    assert isinstance(result, ChatResponse)
    assert len(result.blocks) == 1
    assert result.blocks[0].text == "This is not covered in the video."
    assert result.blocks[0].cites == []
    assert result.follow_ups == []


@pytest.mark.asyncio
async def test_valid_citation_mapping(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    gemini_payload = {
        "answer": [
            {
                "text": "The lecture begins with an introduction.",
                "cites": ["c0"],
            }
        ],
        "follow_ups": ["What comes next?"],
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(gemini_payload)
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="How does it start?",
        chunks=sample_chunks,
    )

    assert isinstance(result, ChatResponse)
    assert len(result.blocks) == 1
    block = result.blocks[0]
    assert isinstance(block, AnswerBlock)
    assert block.text == "The lecture begins with an introduction."
    assert len(block.cites) == 1
    citation = block.cites[0]
    assert isinstance(citation, Citation)
    assert citation.chunk_id == "c0"
    assert citation.seconds == 75.0
    assert citation.label == "01:15"
    assert result.follow_ups == ["What comes next?"]


@pytest.mark.asyncio
async def test_hallucinated_chunk_id_is_dropped(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    gemini_payload = {
        "answer": [
            {
                "text": "Attention mechanisms are explained in detail.",
                "cites": ["c1", "c99", "c-invalid"],
            }
        ],
        "follow_ups": ["Can you explain more?"],
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(gemini_payload)
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="What about attention?",
        chunks=sample_chunks,
    )

    assert len(result.blocks) == 1
    block = result.blocks[0]
    assert len(block.cites) == 1
    assert block.cites[0].chunk_id == "c1"
    assert block.cites[0].label == "12:45"
    assert block.cites[0].seconds == 765.0


@pytest.mark.asyncio
async def test_multiple_citations_and_deduplication(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    gemini_payload = {
        "answer": [
            {
                "text": "Both the beginning and end are discussed.",
                "cites": ["c0", "c2", "c0"],
            }
        ],
        "follow_ups": ["Q1?", "Q2?", "Q3?", "Q4?"],
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(gemini_payload)
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="Summarize the structure",
        chunks=sample_chunks,
    )

    assert len(result.blocks) == 1
    cites = result.blocks[0].cites
    assert len(cites) == 2
    assert [c.chunk_id for c in cites] == ["c0", "c2"]
    assert cites[1].label == "01:01:05"
    assert cites[1].seconds == 3665.0
    assert len(result.follow_ups) == 3


@pytest.mark.asyncio
async def test_structured_parsed_object_support(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = GeminiResponseSchema(
        answer=[
            GeminiAnswerBlock(
                text="The conclusion covers future work.",
                cites=["c2"],
            )
        ],
        follow_ups=["What are the open questions?"],
    )
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="What is at the end?",
        chunks=sample_chunks,
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].text == "The conclusion covers future work."
    assert len(result.blocks[0].cites) == 1
    assert result.blocks[0].cites[0].chunk_id == "c2"
    assert result.blocks[0].cites[0].label == "01:01:05"


@pytest.mark.asyncio
async def test_markdown_code_fence_json_support(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    raw_json = json.dumps({
        "answer": [{"text": "Found it.", "cites": ["c0"]}],
        "follow_ups": [],
    })
    mock_response = MagicMock()
    mock_response.text = f"```json\n{raw_json}\n```"
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="Where is it?",
        chunks=sample_chunks,
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].text == "Found it."
    assert result.blocks[0].cites[0].chunk_id == "c0"


@pytest.mark.asyncio
async def test_with_chat_history(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "answer": [{"text": "Follow up answer.", "cites": ["c1"]}],
        "follow_ups": [],
    })
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    history = [
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello"),
    ]

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="Tell me more",
        chunks=sample_chunks,
        history=history,
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].text == "Follow up answer."
    assert mock_client.models.generate_content.called


@pytest.mark.asyncio
async def test_async_generate_content_support(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "answer": [{"text": "Handled async.", "cites": ["c0"]}],
        "follow_ups": [],
    })
    mock_response.parsed = None
    mock_client.models.generate_content = AsyncMock(return_value=mock_response)

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="Async call test?",
        chunks=sample_chunks,
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].text == "Handled async."


@pytest.mark.asyncio
async def test_empty_answer_blocks_fallback(sample_chunks: list[Chunk]) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"answer": [], "follow_ups": []})
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    result = await synth.synthesize(
        question="Unknown question?",
        chunks=sample_chunks,
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].text == "This is not covered in the video."
    assert result.blocks[0].cites == []


@pytest.mark.asyncio
async def test_llm_api_failure_raises_llm_failed_error(
    sample_chunks: list[Chunk],
) -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Google API network timeout")

    synth = Synthesizer(client=mock_client)
    with pytest.raises(LLMFailedError, match="Gemini API call failed"):
        await synth.synthesize(question="Will fail?", chunks=sample_chunks)


@pytest.mark.asyncio
async def test_empty_response_text_raises_llm_failed_error(
    sample_chunks: list[Chunk],
) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    with pytest.raises(LLMFailedError, match="Gemini returned empty response text"):
        await synth.synthesize(question="Empty text?", chunks=sample_chunks)


@pytest.mark.asyncio
async def test_invalid_json_raises_llm_failed_error(
    sample_chunks: list[Chunk],
) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is definitely not JSON {{"
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    synth = Synthesizer(client=mock_client)
    with pytest.raises(LLMFailedError, match="Failed to parse structured JSON"):
        await synth.synthesize(question="Invalid JSON?", chunks=sample_chunks)
