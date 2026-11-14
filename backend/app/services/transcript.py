from __future__ import annotations

import asyncio
import logging
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
)
from youtube_transcript_api.proxies import GenericProxyConfig

from app.schemas import TranscriptLine

logger = logging.getLogger(__name__)

BLOCKED_KEYWORDS = (
    "blocked",
    "ip address",
    "ip block",
    "429",
    "too many requests",
    "rate limit",
    "requestblocked",
    "cloud ip",
)


class TranscriptError(Exception):
    """Base exception for transcript retrieval errors."""


class NoCaptionsError(TranscriptError):
    """Raised when no captions or transcripts are available for a video."""


class VideoUnavailableError(TranscriptError):
    """Raised when the video is unavailable, deleted, private, or invalid."""


class TranscriptBlockedError(TranscriptError):
    """Raised when YouTube blocks the IP or rate limits transcript requests."""


def _map_exception(exc: Exception, video_id: str) -> TranscriptError:
    """Map external exceptions to strongly-typed domain transcript exceptions."""
    if isinstance(exc, TranscriptError):
        return exc

    exc_class_name = exc.__class__.__name__
    exc_msg = str(exc).lower()

    # 1. Check known specific caption exceptions first
    if (
        isinstance(exc, TranscriptsDisabled | NoTranscriptFound)
        or "notranscript" in exc_class_name.lower()
        or "transcriptdisabled" in exc_class_name.lower()
    ):
        return NoCaptionsError(
            f"No captions available for video '{video_id}': {exc}"
        )

    # 2. Check known video availability exceptions
    if (
        isinstance(exc, VideoUnavailable | VideoUnplayable | InvalidVideoId)
        or exc_class_name in ("VideoUnavailable", "VideoUnplayable", "InvalidVideoId")
    ):
        return VideoUnavailableError(
            f"Video '{video_id}' is unavailable or invalid: {exc}"
        )

    # 3. Check for blocked/IP/rate limit errors (by class or message)
    if (
        isinstance(exc, RequestBlocked | IpBlocked)
        or exc_class_name in ("RequestBlocked", "IpBlocked")
        or any(keyword in exc_msg for keyword in BLOCKED_KEYWORDS)
    ):
        return TranscriptBlockedError(
            f"YouTube blocked the transcript request for video '{video_id}': {exc}"
        )

    # 4. Fallback general transcript error
    return TranscriptError(f"Failed to fetch transcript for video '{video_id}': {exc}")


def _normalize_snippets(raw: Any) -> list[dict]:
    """Convert raw YouTube transcript snippets into normalized dictionaries.

    Returns a list of dicts with 'start', 'duration', and 'text' keys.
    """
    if hasattr(raw, "to_raw_data") and callable(getattr(raw, "to_raw_data")):
        raw = raw.to_raw_data()

    if not isinstance(raw, list | tuple):
        try:
            raw = list(raw)
        except Exception as exc:
            raise TranscriptError(f"Unexpected transcript response format: {type(raw)}") from exc

    normalized: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            start = float(item.get("start", item.get("start_s", 0.0)))
            duration = float(item.get("duration", 0.0))
            text = str(item.get("text", "")).strip()
        else:
            start = float(getattr(item, "start", getattr(item, "start_s", 0.0)))
            duration = float(getattr(item, "duration", 0.0))
            text = str(getattr(item, "text", "")).strip()

        normalized.append(
            {
                "start": round(start, 2),
                "duration": round(duration, 2),
                "text": text,
            }
        )
    return normalized


def _get_api_instance(proxy_url: str | None = None) -> Any:
    """Instantiate YouTubeTranscriptApi with proxy configuration if provided."""
    if not proxy_url:
        return YouTubeTranscriptApi()

    # Try GenericProxyConfig (official youtube-transcript-api >= 1.2.0)
    try:
        proxy_config = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        return YouTubeTranscriptApi(proxy_config=proxy_config)
    except (TypeError, AttributeError):
        pass

    # Try proxies keyword argument (for mocks or alternative wrappers)
    proxies_dict = {"http": proxy_url, "https": proxy_url}
    try:
        return YouTubeTranscriptApi(proxies=proxies_dict)  # type: ignore[call-arg]
    except TypeError:
        return YouTubeTranscriptApi()


def _fetch_transcript_sync(video_id: str, proxy_url: str | None = None) -> list[dict]:
    """Synchronous internal implementation of transcript fetching."""
    try:
        # Check if get_transcript is patched/defined on YouTubeTranscriptApi class
        if (
            hasattr(YouTubeTranscriptApi, "get_transcript")
            and "get_transcript" in YouTubeTranscriptApi.__dict__
            and callable(getattr(YouTubeTranscriptApi, "get_transcript"))
        ):
            proxies_dict = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                raw = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies_dict)
            except TypeError:
                raw = YouTubeTranscriptApi.get_transcript(video_id)
            return _normalize_snippets(raw)

        api = _get_api_instance(proxy_url)

        # Call fetch on the instance (standard 1.2.3 API)
        if hasattr(api, "fetch") and callable(getattr(api, "fetch")):
            try:
                raw = api.fetch(video_id)
            except Exception as initial_exc:
                exc_name = type(initial_exc).__name__
                if (
                    isinstance(initial_exc, NoTranscriptFound)
                    or "notranscript" in exc_name.lower()
                ) and hasattr(api, "list") and callable(getattr(api, "list")):
                    try:
                        transcript_list = api.list(video_id)
                        transcripts = list(transcript_list)
                        if not transcripts:
                            raise initial_exc
                        manual = [t for t in transcripts if not getattr(t, "is_generated", False)]
                        chosen = manual[0] if manual else transcripts[0]
                        raw = chosen.fetch()
                    except Exception:
                        raise initial_exc
                else:
                    raise initial_exc
        elif hasattr(api, "get_transcript") and callable(getattr(api, "get_transcript")):
            proxies_dict = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                raw = api.get_transcript(video_id, proxies=proxies_dict)
            except TypeError:
                raw = api.get_transcript(video_id)
        elif (
            hasattr(YouTubeTranscriptApi, "get_transcript")
            and callable(getattr(YouTubeTranscriptApi, "get_transcript"))
        ):
            proxies_dict = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                raw = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies_dict)
            except TypeError:
                raw = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            raise TranscriptError(f"Unsupported YouTubeTranscriptApi interface on {type(api)}")

        return _normalize_snippets(raw)
    except Exception as exc:
        raise _map_exception(exc, video_id) from exc


async def fetch_transcript(
    video_id: str,
    proxy_url: str | None = None,
) -> list[dict]:
    """Fetch video transcript from YouTube asynchronously.

    Runs synchronous API calls in a worker thread to keep the asyncio event loop responsive.

    Parameters:
        video_id: 11-character YouTube video ID.
        proxy_url: Optional proxy URL (e.g. 'http://user:pass@host:port').

    Returns:
        List of raw snippet dictionaries with 'start', 'duration', and 'text'.

    Raises:
        NoCaptionsError: If captions are disabled or unavailable.
        VideoUnavailableError: If the video is private, deleted, or unplayable.
        TranscriptBlockedError: If YouTube blocks the request (IP ban / 429).
        TranscriptError: For other transcript retrieval errors.
    """
    clean_video_id = video_id.strip()
    return await asyncio.to_thread(_fetch_transcript_sync, clean_video_id, proxy_url)


def group_transcript_lines(
    raw_snippets: list[dict],
    target_duration_s: float = 12.0,
) -> list[TranscriptLine]:
    """Group raw transcript snippets into lines spanning approximately target_duration_s (~10-15s).

    Parameters:
        raw_snippets: List of raw transcript snippet dicts with 'start' and 'text'.
        target_duration_s: Target duration in seconds for each grouped line (default 12.0).

    Returns:
        List of TranscriptLine instances with 'start_s' and 'text'.
    """
    if not raw_snippets:
        return []

    lines: list[TranscriptLine] = []
    current_texts: list[str] = []
    current_start: float | None = None
    current_end: float = 0.0

    for snippet in raw_snippets:
        raw_text = str(snippet.get("text", "")).strip()
        if not raw_text:
            continue

        start = float(snippet.get("start", snippet.get("start_s", 0.0)))
        duration = float(snippet.get("duration", 0.0))
        end = start + max(duration, 0.0)

        if current_start is None:
            current_start = start
            current_texts = [raw_text]
            current_end = max(end, start)
            continue

        span_if_included = max(end, current_end) - current_start
        gap = start - current_end

        # Group into ~10-15s: if adding this snippet exceeds target_duration_s
        # or there is >5s silence
        if span_if_included > target_duration_s or gap > 5.0:
            if current_texts:
                lines.append(
                    TranscriptLine(
                        start_s=round(current_start, 2),
                        text=" ".join(current_texts),
                    )
                )
            current_start = start
            current_texts = [raw_text]
            current_end = max(end, start)
        else:
            current_texts.append(raw_text)
            current_end = max(current_end, end)

    if current_start is not None and current_texts:
        lines.append(
            TranscriptLine(
                start_s=round(current_start, 2),
                text=" ".join(current_texts),
            )
        )

    return lines
