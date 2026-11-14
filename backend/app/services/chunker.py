from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    start_s: float
    end_s: float


def _get_start(seg: dict[str, Any]) -> float:
    val = seg.get("start")
    if val is None:
        val = seg.get("start_s", 0.0)
    try:
        v = float(val)
        return 0.0 if (math.isnan(v) or math.isinf(v)) else v
    except (ValueError, TypeError):
        return 0.0


def _get_duration(seg: dict[str, Any]) -> float:
    val = seg.get("duration", 0.0)
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return max(0.0, v)
    except (ValueError, TypeError):
        return 0.0


def _clean_text(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).split())


def chunk_transcript(
    segments: list[dict[str, Any]],
    window_s: float = 60.0,
    max_words: int = 220,
    overlap_frac: float = 0.20,
) -> list[Chunk]:
    """Chunk transcript segments into overlapping windows.

    Args:
        segments: List of dicts with 'start' (or 'start_s'), 'duration', and 'text'.
        window_s: Target maximum chunk duration in seconds.
        max_words: Target maximum word count per chunk.
        overlap_frac: Fraction of overlap for sliding window (e.g. 0.20 = 20%).

    Returns:
        List of Chunk dataclasses.
    """
    if not segments:
        return []

    # Sanitize parameters
    if math.isnan(window_s) or math.isinf(window_s):
        eff_window_s = 60.0
    else:
        eff_window_s = window_s

    if math.isnan(overlap_frac) or math.isinf(overlap_frac):
        eff_overlap_frac = 0.20
    else:
        eff_overlap_frac = overlap_frac

    eff_max_words = max_words

    # Sort segments chronologically by start timestamp to ensure proper sequential chunking
    sorted_segments = sorted(segments, key=_get_start)
    n_segments = len(sorted_segments)

    chunks: list[Chunk] = []
    start_idx = 0

    while start_idx < n_segments:
        first_seg = sorted_segments[start_idx]
        start_s = _get_start(first_seg)

        end_idx = start_idx
        accumulated_texts: list[str] = []

        seg_text = _clean_text(first_seg.get("text", ""))
        accumulated_texts.append(seg_text)
        total_words = len(seg_text.split())

        cur_end = start_s + _get_duration(first_seg)
        cur_duration = max(0.0, cur_end - start_s)

        while end_idx + 1 < n_segments:
            # Stop accumulating if duration reaches window_s or word count reaches max_words
            if cur_duration >= eff_window_s or total_words >= eff_max_words:
                break

            end_idx += 1
            next_seg = sorted_segments[end_idx]
            next_text = _clean_text(next_seg.get("text", ""))
            accumulated_texts.append(next_text)
            total_words += len(next_text.split())

            seg_end = _get_start(next_seg) + _get_duration(next_seg)
            cur_end = max(cur_end, seg_end)
            cur_duration = max(0.0, cur_end - start_s)

        end_s = max(start_s, cur_end)
        chunk_duration = end_s - start_s

        chunk_text = " ".join(t for t in accumulated_texts if t)
        chunk_id = f"c{len(chunks)}"

        chunks.append(
            Chunk(
                id=chunk_id,
                text=chunk_text,
                start_s=start_s,
                end_s=end_s,
            )
        )

        # If the current chunk reached the end of the segments, stop
        if end_idx >= n_segments - 1:
            break

        # Slide forward to achieve overlap_frac overlap
        target_start = start_s + (1.0 - eff_overlap_frac) * chunk_duration
        candidates = range(start_idx + 1, n_segments)
        next_start_idx = min(
            candidates,
            key=lambda idx: abs(_get_start(sorted_segments[idx]) - target_start),
        )
        # Ensure progress to prevent infinite loops
        start_idx = max(start_idx + 1, next_start_idx)

    return chunks
