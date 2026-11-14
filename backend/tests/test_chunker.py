from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.chunker import Chunk, chunk_transcript

# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


def test_empty_input() -> None:
    """Empty segments list must return an empty list."""
    assert chunk_transcript([]) == []


def test_single_short_segment() -> None:
    """A single short segment should produce a single chunk matching the segment."""
    segments = [
        {"start": 0.0, "duration": 5.0, "text": "Welcome to this tutorial."},
    ]
    chunks = chunk_transcript(segments)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk == Chunk(
        id="c0",
        text="Welcome to this tutorial.",
        start_s=0.0,
        end_s=5.0,
    )


def test_single_huge_segment() -> None:
    """A single segment exceeding window duration and word count must still produce one chunk."""
    huge_text = " ".join([f"word{i}" for i in range(500)])
    segments = [
        {"start": 10.0, "duration": 900.0, "text": huge_text},
    ]
    chunks = chunk_transcript(segments, window_s=60.0, max_words=220)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.id == "c0"
    assert chunk.start_s == 10.0
    assert chunk.end_s == 910.0
    assert chunk.text == huge_text


def test_realistic_10_minute_transcript() -> None:
    """Realistic 10-minute transcript (600s, 60 segments) must chunk correctly with overlap."""
    segments = []
    for i in range(60):
        start = float(i * 10)
        duration = 10.0
        text = f"Segment {i} explains section {i // 6} with introductory and concluding remarks."
        segments.append({"start": start, "duration": duration, "text": text})

    chunks = chunk_transcript(segments, window_s=60.0, max_words=220, overlap_frac=0.20)

    # 600s with 60s windows and ~20% overlap (~48s step) should produce around 11-14 chunks
    assert len(chunks) > 1
    assert chunks[0].id == "c0"
    assert chunks[0].start_s == 0.0
    assert chunks[-1].end_s == 600.0

    # Verify sequential IDs and monotonicity
    for i, chunk in enumerate(chunks):
        assert chunk.id == f"c{i}"
        assert re.fullmatch(r"c\d+", chunk.id) is not None
        assert chunk.end_s >= chunk.start_s
        assert len(chunk.text.strip()) > 0
        if i > 0:
            assert chunk.start_s >= chunks[i - 1].start_s
            # Overlap check: next chunk starts before previous chunk ends
            assert chunk.start_s < chunks[i - 1].end_s


def test_start_s_key_alias() -> None:
    """Supports 'start_s' key when 'start' is not present."""
    segments = [
        {"start_s": 15.0, "duration": 10.0, "text": "First part."},
        {"start_s": 25.0, "duration": 10.0, "text": "Second part."},
    ]
    chunks = chunk_transcript(segments, window_s=60.0)

    assert len(chunks) == 1
    assert chunks[0].start_s == 15.0
    assert chunks[0].end_s == 35.0
    assert chunks[0].text == "First part. Second part."


def test_text_cleaning_and_whitespace() -> None:
    """Extra newlines, multiple spaces, and tabs should be normalized into single spaces."""
    segments = [
        {"start": 0.0, "duration": 5.0, "text": "  Hello \n\n  world!  \t "},
        {"start": 5.0, "duration": 5.0, "text": "Next   line   here.  "},
    ]
    chunks = chunk_transcript(segments, window_s=60.0)

    assert len(chunks) == 1
    assert chunks[0].text == "Hello world! Next line here."


def test_max_words_threshold() -> None:
    """Accumulation stops when word count reaches max_words even if window_s is not reached."""
    # 3 segments, each 10 words, duration 5s each
    segments = [
        {"start": 0.0, "duration": 5.0, "text": "one two three four five six seven eight nine ten"},
        {
            "start": 5.0,
            "duration": 5.0,
            "text": "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen",
        },
        {"start": 10.0, "duration": 5.0, "text": "twenty-one twenty-two twenty-three twenty-four"},
    ]
    # Set max_words=15 so first chunk stops after second segment
    chunks = chunk_transcript(segments, window_s=100.0, max_words=15, overlap_frac=0.0)

    assert len(chunks) >= 2
    # Chunk 0 accumulated first 2 segments
    assert chunks[0].start_s == 0.0
    assert chunks[0].end_s == 10.0
    assert "nineteen" in chunks[0].text


def test_window_duration_threshold() -> None:
    """Accumulation stops when duration reaches window_s even if max_words is not reached."""
    segments = [
        {"start": 0.0, "duration": 25.0, "text": "Short intro."},
        {"start": 25.0, "duration": 25.0, "text": "Middle part."},
        {"start": 50.0, "duration": 25.0, "text": "Ending part."},
    ]
    # window_s=40.0 should split after second segment (50s >= 40s)
    chunks = chunk_transcript(segments, window_s=40.0, max_words=500, overlap_frac=0.0)

    assert len(chunks) >= 2
    assert chunks[0].start_s == 0.0
    assert chunks[0].end_s == 50.0
    assert chunks[0].text == "Short intro. Middle part."


def test_custom_overlap_fraction() -> None:
    """Changing overlap_frac modifies next chunk starting point."""
    segments = [
        {"start": float(i * 10), "duration": 10.0, "text": f"text {i}"}
        for i in range(10)
    ]
    # overlap_frac = 0.0 -> no overlap (step ~ 100% of duration)
    chunks_no_overlap = chunk_transcript(segments, window_s=30.0, overlap_frac=0.0)
    # overlap_frac = 0.50 -> 50% overlap
    chunks_half_overlap = chunk_transcript(segments, window_s=30.0, overlap_frac=0.50)

    # 50% overlap should produce more chunks than 0% overlap
    assert len(chunks_half_overlap) > len(chunks_no_overlap)


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

arbitrary_segment_strategy = st.fixed_dictionaries(
    {
        "start": st.floats(
            min_value=-1000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
        "duration": st.floats(
            min_value=-10.0, max_value=500.0, allow_nan=False, allow_infinity=False
        ),
        "text": st.text(max_size=120),
    }
)

segment_with_text_strategy = st.fixed_dictionaries(
    {
        "start": st.floats(
            min_value=0.0, max_value=7200.0, allow_nan=False, allow_infinity=False
        ),
        "duration": st.floats(
            min_value=0.1, max_value=120.0, allow_nan=False, allow_infinity=False
        ),
        "text": st.text(
            alphabet=st.characters(categories=("L", "N", "Z")),
            min_size=1,
            max_size=80,
        ).filter(lambda s: bool(s.strip())),
    }
)


@given(
    segments=st.lists(arbitrary_segment_strategy, min_size=0, max_size=35),
    window_s=st.floats(min_value=1.0, max_value=300.0, allow_nan=False, allow_infinity=False),
    max_words=st.integers(min_value=1, max_value=500),
    overlap_frac=st.floats(min_value=0.0, max_value=0.9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_property_chunks_ordered_by_start_s(
    segments: list[dict],
    window_s: float,
    max_words: int,
    overlap_frac: float,
) -> None:
    """Ensure chunks are always ordered monotonically by start_s."""
    chunks = chunk_transcript(
        segments,
        window_s=window_s,
        max_words=max_words,
        overlap_frac=overlap_frac,
    )
    for i in range(len(chunks) - 1):
        assert chunks[i].start_s <= chunks[i + 1].start_s


@given(
    segments=st.lists(arbitrary_segment_strategy, min_size=0, max_size=35),
)
@settings(max_examples=100)
def test_property_chunk_ids_follow_format(segments: list[dict]) -> None:
    r"""Ensure every chunk ID follows the c\d+ pattern and is strictly sequential."""
    chunks = chunk_transcript(segments)
    for i, chunk in enumerate(chunks):
        assert chunk.id == f"c{i}"
        assert re.fullmatch(r"c\d+", chunk.id) is not None


@given(
    segments=st.lists(segment_with_text_strategy, min_size=1, max_size=35),
    window_s=st.floats(min_value=5.0, max_value=120.0, allow_nan=False, allow_infinity=False),
    max_words=st.integers(min_value=10, max_value=300),
    overlap_frac=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_property_non_empty_text_when_segments_have_text(
    segments: list[dict],
    window_s: float,
    max_words: int,
    overlap_frac: float,
) -> None:
    """Ensure every chunk has non-empty text when input segments have non-empty text."""
    chunks = chunk_transcript(
        segments,
        window_s=window_s,
        max_words=max_words,
        overlap_frac=overlap_frac,
    )
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.text.strip()) > 0


@given(
    segments=st.lists(
        st.dictionaries(
            keys=st.sampled_from(["start", "start_s", "duration", "text", "other"]),
            values=st.one_of(
                st.floats(allow_nan=True, allow_infinity=True),
                st.integers(),
                st.text(max_size=50),
                st.none(),
            ),
            max_size=5,
        ),
        min_size=0,
        max_size=30,
    ),
    window_s=st.one_of(
        st.floats(min_value=-50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        st.just(float("nan")),
        st.just(float("inf")),
    ),
    max_words=st.integers(min_value=-10, max_value=200),
    overlap_frac=st.one_of(
        st.floats(min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        st.just(float("nan")),
        st.just(float("inf")),
    ),
)
@settings(max_examples=100)
def test_property_termination_on_all_inputs(
    segments: list[dict],
    window_s: float,
    max_words: int,
    overlap_frac: float,
) -> None:
    """Ensure chunk_transcript always terminates without infinite loops on any inputs."""
    chunks = chunk_transcript(
        segments,
        window_s=window_s,
        max_words=max_words,
        overlap_frac=overlap_frac,
    )
    assert isinstance(chunks, list)
    for chunk in chunks:
        assert isinstance(chunk, Chunk)
        assert isinstance(chunk.id, str)
        assert isinstance(chunk.text, str)
        assert isinstance(chunk.start_s, float)
        assert isinstance(chunk.end_s, float)
