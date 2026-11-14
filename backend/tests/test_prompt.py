from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from google.genai._transformers import t_contents

from app.schemas import ChatMessage
from app.services.prompt import (
    SYSTEM_PROMPT,
    GeminiAnswerBlock,
    GeminiResponseSchema,
    build_prompt_contents,
)


@dataclass
class DummyChunk:
    id: str
    text: str
    start_s: float = 0.0
    end_s: float = 10.0


def test_system_prompt_rules() -> None:
    assert "TimeSliceIQ" in SYSTEM_PROMPT
    assert "transcript chunks" in SYSTEM_PROMPT
    assert "This is not covered in the video." in SYSTEM_PROMPT
    assert "cites" in SYSTEM_PROMPT
    assert "timestamps" in SYSTEM_PROMPT.lower()
    assert "untrusted" in SYSTEM_PROMPT.lower()
    assert "follow_ups" in SYSTEM_PROMPT


def test_gemini_models_schema() -> None:
    block = GeminiAnswerBlock(text="Attention mechanism is introduced.", cites=["c0"])
    assert block.text == "Attention mechanism is introduced."
    assert block.cites == ["c0"]

    schema = GeminiResponseSchema(
        answer=[block],
        follow_ups=["How does multi-head attention work?"],
    )
    assert len(schema.answer) == 1
    assert len(schema.follow_ups) == 1

    dumped = schema.model_dump()
    assert dumped["answer"][0]["cites"] == ["c0"]
    assert dumped["follow_ups"] == ["How does multi-head attention work?"]

    # Test JSON schema generation
    json_schema = GeminiResponseSchema.model_json_schema()
    assert "answer" in json_schema["properties"]
    assert "follow_ups" in json_schema["properties"]


def test_build_prompt_contents_no_history() -> None:
    chunks = [
        DummyChunk(id="c0", text="Introductory overview of transformers."),
        DummyChunk(id="c1", text="Scaled dot-product attention explanation."),
    ]
    contents = build_prompt_contents(
        question="What is scaled dot-product attention?",
        chunks=chunks,
    )
    assert isinstance(contents, list)
    assert len(contents) == 1
    prompt_str = contents[0]
    assert isinstance(prompt_str, str)
    assert "[c0] Introductory overview" in prompt_str
    assert "[c1] Scaled dot-product" in prompt_str
    assert "USER QUESTION: What is scaled dot-product attention?" in prompt_str

    # Validate that google-genai transformer accepts it
    transformed = t_contents(None, contents)
    assert len(transformed) == 1
    assert transformed[0].role == "user"


def test_build_prompt_contents_with_dict_chunks() -> None:
    chunks = [
        {"id": "c0", "text": "Dict chunk 0"},
        {"id": "c1", "text": "Dict chunk 1"},
    ]
    contents = build_prompt_contents("Test question", chunks)
    assert "[c0] Dict chunk 0" in contents[0]
    assert "[c1] Dict chunk 1" in contents[0]


def test_build_prompt_contents_with_history() -> None:
    chunks = [DummyChunk(id="c0", text="Some content")]
    history = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi! How can I help?"),
        {"role": "user", "content": "What is attention?"},
        {"role": "assistant", "content": "Attention is a neural mechanism."},
    ]

    contents = build_prompt_contents(
        question="How does it work?",
        chunks=chunks,
        history=history,
    )

    assert isinstance(contents, list)
    # 4 history messages + 1 current question = 5 messages
    assert len(contents) == 5
    assert contents[0] == {"role": "user", "parts": [{"text": "Hello"}]}
    assert contents[1] == {"role": "model", "parts": [{"text": "Hi! How can I help?"}]}
    assert contents[2] == {"role": "user", "parts": [{"text": "What is attention?"}]}
    assert contents[3] == {
        "role": "model",
        "parts": [{"text": "Attention is a neural mechanism."},
    ]}
    assert contents[4]["role"] == "user"
    assert "How does it work?" in contents[4]["parts"][0]["text"]

    # Validate with google-genai transformer
    transformed = t_contents(None, contents)
    assert len(transformed) == 5
    assert [t.role for t in transformed] == ["user", "model", "user", "model", "user"]


def test_build_prompt_contents_history_max_6() -> None:
    chunks = [DummyChunk(id="c0", text="Content")]
    history = [ChatMessage(role="user", content=f"Message {i}") for i in range(10)]

    contents = build_prompt_contents("Current question", chunks, history=history)
    # 6 history messages + 1 current message = 7
    assert len(contents) == 7
    # Should contain Message 4 through Message 9
    assert contents[0] == {"role": "user", "parts": [{"text": "Message 4"}]}
    assert contents[5] == {"role": "user", "parts": [{"text": "Message 9"}]}


def test_eval_questions_dataset() -> None:
    eval_path = Path(__file__).resolve().parent.parent / "eval" / "questions.json"
    assert eval_path.exists()

    with eval_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 10

    required_categories = {
        "direct_factual_recall",
        "multi_chunk_synthesis",
        "off_topic",
        "prompt_injection",
        "timestamp_seeking",
        "mathematical_or_technical_concept_explanation",
        "speaker_opinion_vs_fact",
        "ambiguous_question",
        "summary_of_lecture",
        "negative_query",
    }
    actual_categories = {item["category"] for item in data}
    assert required_categories == actual_categories

    for item in data:
        assert "id" in item
        assert "question" in item
        assert "chunks" in item
        assert len(item["chunks"]) > 0
        assert "expected" in item
        assert "is_covered" in item["expected"]
        assert "expected_cites" in item["expected"]

        # Verify build_prompt_contents works with all eval items
        contents = build_prompt_contents(item["question"], item["chunks"])
        assert len(contents) == 1
        assert item["question"] in contents[0]
