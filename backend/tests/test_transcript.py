from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
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
from app.services.transcript import (
    NoCaptionsError,
    TranscriptBlockedError,
    TranscriptError,
    VideoUnavailableError,
    fetch_transcript,
    group_transcript_lines,
)


class CustomNoTranscriptAvailable(Exception):
    """Custom exception simulating older or third-party NoTranscriptAvailable."""


# =====================================================================
# Typed Exception Hierarchy Tests
# =====================================================================


def test_exception_hierarchy():
    assert issubclass(NoCaptionsError, TranscriptError)
    assert issubclass(VideoUnavailableError, TranscriptError)
    assert issubclass(TranscriptBlockedError, TranscriptError)
    assert issubclass(TranscriptError, Exception)


# =====================================================================
# Fetch Transcript Success Tests
# =====================================================================


@pytest.mark.asyncio
async def test_fetch_transcript_success_dicts():
    raw_snippets = [
        {"start": 0.0, "duration": 2.5, "text": "Welcome to the lecture."},
        {"start": 2.5, "duration": 3.2, "text": "Today we cover algorithms."},
    ]
    mock_instance = MagicMock()
    mock_instance.fetch.return_value = raw_snippets

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        result = await fetch_transcript("dQw4w9WgXcQ")

    assert len(result) == 2
    assert result[0] == {"start": 0.0, "duration": 2.5, "text": "Welcome to the lecture."}
    assert result[1] == {"start": 2.5, "duration": 3.2, "text": "Today we cover algorithms."}
    mock_instance.fetch.assert_called_once_with("dQw4w9WgXcQ")


@pytest.mark.asyncio
async def test_fetch_transcript_with_to_raw_data_object():
    class DummyFetchedTranscript:
        def to_raw_data(self):
            return [{"start": 1.234, "duration": 4.567, "text": "Normalized text"}]

    mock_instance = MagicMock()
    mock_instance.fetch.return_value = DummyFetchedTranscript()

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        result = await fetch_transcript("abc12345678")

    assert result == [{"start": 1.23, "duration": 4.57, "text": "Normalized text"}]


@pytest.mark.asyncio
async def test_fetch_transcript_with_snippet_objects():
    class DummySnippet:
        def __init__(self, start: float, duration: float, text: str):
            self.start = start
            self.duration = duration
            self.text = text

    mock_instance = MagicMock()
    mock_instance.fetch.return_value = [
        DummySnippet(start=0.5, duration=3.0, text="Snippet object")
    ]

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        result = await fetch_transcript("abc12345678")

    assert result == [{"start": 0.5, "duration": 3.0, "text": "Snippet object"}]


# =====================================================================
# Proxy Argument Verification Tests
# =====================================================================


@pytest.mark.asyncio
async def test_fetch_transcript_with_proxy_url():
    mock_instance = MagicMock()
    mock_instance.fetch.return_value = [{"start": 0.0, "duration": 1.0, "text": "Proxied"}]

    proxy_url = "http://user:pass@proxy.corp.internal:8080"
    with patch(
        "app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance
    ) as mock_cls:
        result = await fetch_transcript("vid12345678", proxy_url=proxy_url)

    assert result == [{"start": 0.0, "duration": 1.0, "text": "Proxied"}]
    mock_cls.assert_called_once()
    call_kwargs = mock_cls.call_args.kwargs
    assert "proxy_config" in call_kwargs
    proxy_config = call_kwargs["proxy_config"]
    assert isinstance(proxy_config, GenericProxyConfig)
    assert proxy_config.http_url == proxy_url
    assert proxy_config.https_url == proxy_url


@pytest.mark.asyncio
async def test_fetch_transcript_proxy_fallback_to_proxies_kwarg():
    mock_instance = MagicMock()
    mock_instance.fetch.return_value = [{"start": 0.0, "duration": 1.0, "text": "Fallback"}]

    proxy_url = "http://user:pass@proxy.corp.internal:8080"

    def mock_init(*args, **kwargs):
        if "proxy_config" in kwargs:
            raise TypeError("Mock does not support proxy_config")
        return mock_instance

    with patch("app.services.transcript.YouTubeTranscriptApi", side_effect=mock_init) as mock_cls:
        result = await fetch_transcript("vid12345678", proxy_url=proxy_url)

    assert result == [{"start": 0.0, "duration": 1.0, "text": "Fallback"}]
    assert mock_cls.call_count == 2
    second_call_kwargs = mock_cls.call_args_list[1].kwargs
    assert second_call_kwargs.get("proxies") == {"http": proxy_url, "https": proxy_url}


# =====================================================================
# Exception Mapping Tests
# =====================================================================


@pytest.mark.asyncio
async def test_fetch_transcript_transcripts_disabled():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = TranscriptsDisabled("vid12345678")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(NoCaptionsError) as exc_info:
            await fetch_transcript("vid12345678")

    assert "No captions available" in str(exc_info.value)
    assert "vid12345678" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_transcript_no_transcript_found():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = NoTranscriptFound("vid12345678", ["en"], None)

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(NoCaptionsError) as exc_info:
            await fetch_transcript("vid12345678")

    assert "No captions available" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_transcript_no_transcript_available_custom():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = CustomNoTranscriptAvailable("No transcript is available")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(NoCaptionsError):
            await fetch_transcript("vid12345678")


@pytest.mark.asyncio
async def test_fetch_transcript_video_unavailable():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = VideoUnavailable("vid12345678")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(VideoUnavailableError) as exc_info:
            await fetch_transcript("vid12345678")

    assert "unavailable or invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_transcript_video_unplayable():
    mock_instance = MagicMock()
    try:
        mock_instance.fetch.side_effect = VideoUnplayable("vid12345678", "Video is unplayable", [])
    except TypeError:
        mock_instance.fetch.side_effect = VideoUnplayable("vid12345678")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(VideoUnavailableError):
            await fetch_transcript("vid12345678")


@pytest.mark.asyncio
async def test_fetch_transcript_invalid_video_id():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = InvalidVideoId("bad_id")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(VideoUnavailableError):
            await fetch_transcript("bad_id")


@pytest.mark.asyncio
async def test_fetch_transcript_request_blocked():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = RequestBlocked("vid12345678")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(TranscriptBlockedError) as exc_info:
            await fetch_transcript("vid12345678")

    assert "YouTube blocked the transcript request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_transcript_ip_blocked():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = IpBlocked("vid12345678")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(TranscriptBlockedError):
            await fetch_transcript("vid12345678")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        "Too many requests, status 429",
        "Your IP has been temporarily blocked by YouTube",
        "RequestBlocked: access denied",
        "rate limit exceeded (requestblocked)",
    ],
)
async def test_fetch_transcript_blocked_keywords(error_message: str):
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = RuntimeError(error_message)

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(TranscriptBlockedError):
            await fetch_transcript("vid12345678")


@pytest.mark.asyncio
async def test_fetch_transcript_generic_error():
    mock_instance = MagicMock()
    mock_instance.fetch.side_effect = ConnectionResetError("Connection lost")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=mock_instance):
        with pytest.raises(TranscriptError) as exc_info:
            await fetch_transcript("vid12345678")

    assert "Failed to fetch transcript" in str(exc_info.value)
    # Ensure it is not a subclass like NoCaptionsError or TranscriptBlockedError
    assert type(exc_info.value) is TranscriptError


@pytest.mark.asyncio
async def test_fetch_transcript_legacy_class_method_get_transcript():
    from youtube_transcript_api import YouTubeTranscriptApi

    sample = [{"start": 0.0, "duration": 5.0, "text": "Legacy transcript line"}]
    with patch.object(
        YouTubeTranscriptApi, "get_transcript", create=True, return_value=sample
    ) as mock_gt:
        result = await fetch_transcript("legacysample", proxy_url="http://proxy:8080")

    assert result == [{"start": 0.0, "duration": 5.0, "text": "Legacy transcript line"}]
    mock_gt.assert_called_once_with(
        "legacysample", proxies={"http": "http://proxy:8080", "https": "http://proxy:8080"}
    )


# =====================================================================
# Group Transcript Lines Tests
# =====================================================================


def test_group_transcript_lines_empty():
    assert group_transcript_lines([]) == []
    assert group_transcript_lines([{"text": "", "start": 0.0, "duration": 1.0}]) == []
    assert group_transcript_lines([{"text": "   ", "start": 0.0, "duration": 1.0}]) == []


def test_group_transcript_lines_combines_short_snippets():
    snippets = [
        {"start": 0.0, "duration": 2.0, "text": "First part."},
        {"start": 2.0, "duration": 2.0, "text": "Second part."},
        {"start": 4.0, "duration": 2.0, "text": "Third part."},
        {"start": 6.0, "duration": 2.0, "text": "Fourth part."},
        {"start": 8.0, "duration": 2.0, "text": "Fifth part."},
        {"start": 10.0, "duration": 2.0, "text": "Sixth part."},
        {"start": 12.0, "duration": 2.0, "text": "Seventh part."},
    ]

    lines = group_transcript_lines(snippets, target_duration_s=12.0)
    assert len(lines) == 2

    # First group spans 0.0 to 12.0 (12 seconds)
    assert lines[0] == TranscriptLine(
        start_s=0.0,
        text="First part. Second part. Third part. Fourth part. Fifth part. Sixth part.",
    )
    # Second group starts at 12.0
    assert lines[1] == TranscriptLine(
        start_s=12.0,
        text="Seventh part.",
    )


def test_group_transcript_lines_silence_gap():
    snippets = [
        {"start": 0.0, "duration": 3.0, "text": "Intro speech."},
        # 17 seconds of silence (gap > 5s)
        {"start": 20.0, "duration": 4.0, "text": "Next topic begins here."},
    ]

    lines = group_transcript_lines(snippets, target_duration_s=12.0)
    assert len(lines) == 2
    assert lines[0] == TranscriptLine(start_s=0.0, text="Intro speech.")
    assert lines[1] == TranscriptLine(start_s=20.0, text="Next topic begins here.")


def test_group_transcript_lines_single_long_snippet():
    snippets = [
        {"start": 5.5, "duration": 25.0, "text": "A very long continuous monologue without breaks."}
    ]

    lines = group_transcript_lines(snippets, target_duration_s=12.0)
    assert len(lines) == 1
    assert lines[0] == TranscriptLine(
        start_s=5.5,
        text="A very long continuous monologue without breaks.",
    )


def test_group_transcript_lines_handles_start_s_key_and_whitespace():
    snippets = [
        {"start_s": 1.0, "duration": 2.0, "text": "  Hello \n  world!  "},
        {"start_s": 3.0, "duration": 2.0, "text": "How are you?  "},
    ]

    lines = group_transcript_lines(snippets, target_duration_s=10.0)
    assert len(lines) == 1
    assert lines[0] == TranscriptLine(start_s=1.0, text="Hello \n  world! How are you?")
