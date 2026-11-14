from __future__ import annotations

import pytest

from app.schemas import ErrorCode
from app.services.url_parser import InvalidURLError, parse_youtube_url

EXPECTED_ID = "dQw4w9WgXcQ"


# -----------------------------------------------------------------------------
# Valid URL Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected_id"),
    [
        # Standard watch URLs
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", EXPECTED_ID),
        ("https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/watch?t=100&v=dQw4w9WgXcQ&list=PL123", EXPECTED_ID),
        ("https://www.youtube.com/?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/v/dQw4w9WgXcQ", EXPECTED_ID),
        # Mobile URLs
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&app=m", EXPECTED_ID),
        # youtu.be short URLs
        ("https://youtu.be/dQw4w9WgXcQ", EXPECTED_ID),
        ("http://youtu.be/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://youtu.be/dQw4w9WgXcQ/", EXPECTED_ID),
        ("https://youtu.be/dQw4w9WgXcQ?si=abcdef12345", EXPECTED_ID),
        ("https://youtu.be/dQw4w9WgXcQ?t=120", EXPECTED_ID),
        ("https://youtu.be/dQw4w9WgXcQ?feature=share&si=tracking123", EXPECTED_ID),
        # Shorts URLs
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ/", EXPECTED_ID),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share", EXPECTED_ID),
        # Embed URLs
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ/", EXPECTED_ID),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1", EXPECTED_ID),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ?start=30&autoplay=1", EXPECTED_ID),
        # Privacy-enhanced nocookie URLs
        ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1", EXPECTED_ID),
        ("https://www.youtube-nocookie.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        # Live stream URLs
        ("https://www.youtube.com/live/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/live/dQw4w9WgXcQ/", EXPECTED_ID),
        ("https://www.youtube.com/live/dQw4w9WgXcQ?feature=share", EXPECTED_ID),
        # Schemeless and protocol-relative URLs
        ("www.youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("youtu.be/dQw4w9WgXcQ", EXPECTED_ID),
        ("//www.youtube.com/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        # Whitespace handling
        ("   https://www.youtube.com/watch?v=dQw4w9WgXcQ   ", EXPECTED_ID),
        ("\thttps://youtu.be/dQw4w9WgXcQ\n", EXPECTED_ID),
        # Case insensitivity of scheme and host, but preserves ID casing
        ("HTTPS://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/SHORTS/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/EMBED/dQw4w9WgXcQ", EXPECTED_ID),
        ("https://www.youtube.com/LIVE/dQw4w9WgXcQ", EXPECTED_ID),
        # Distinct 11-char IDs with hyphen and underscore
        ("https://www.youtube.com/watch?v=a1B2-_c3D4E", "a1B2-_c3D4E"),
        ("https://youtu.be/_123456789a", "_123456789a"),
        ("https://youtu.be/123456789-b", "123456789-b"),
    ],
)
def test_parse_youtube_url_valid(url: str, expected_id: str) -> None:
    assert parse_youtube_url(url) == expected_id


# -----------------------------------------------------------------------------
# Invalid Scheme Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "invalid_scheme_url",
    [
        "javascript:alert(1)",
        "javascript://youtube.com/watch?v=dQw4w9WgXcQ",
        "data:text/html,<script>alert(1)</script>",
        "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "file:///path/to/video.mp4",
        "ssh://youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_parse_youtube_url_invalid_schemes(invalid_scheme_url: str) -> None:
    with pytest.raises(InvalidURLError) as exc_info:
        parse_youtube_url(invalid_scheme_url)
    assert exc_info.value.code == ErrorCode.INVALID_URL


# -----------------------------------------------------------------------------
# Non-YouTube Host Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unallowed_host_url",
    [
        "https://vimeo.com/123456789",
        "https://dailymotion.com/video/x7tgad0",
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.attacker.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com.evil.org/watch?v=dQw4w9WgXcQ",
        "https://google.com",
        "https://evil-youtu.be/dQw4w9WgXcQ",
        "https://attacker-youtube-nocookie.com/embed/dQw4w9WgXcQ",
        "https://youtube-nocookie.com.evil/embed/dQw4w9WgXcQ",
    ],
)
def test_parse_youtube_url_unallowed_hosts(unallowed_host_url: str) -> None:
    with pytest.raises(InvalidURLError) as exc_info:
        parse_youtube_url(unallowed_host_url)
    assert "not an allowed YouTube domain" in str(exc_info.value)
    assert exc_info.value.code == ErrorCode.INVALID_URL


# -----------------------------------------------------------------------------
# Invalid Video ID Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "invalid_id_url",
    [
        # 10 chars (too short)
        "https://www.youtube.com/watch?v=dQw4w9WgXc",
        # 12 chars (too long)
        "https://www.youtube.com/watch?v=dQw4w9WgXcQQ",
        # Invalid characters
        "https://www.youtube.com/watch?v=dQw4w9WgXc$",
        "https://www.youtube.com/watch?v=dQw4w9WgXc!",
        "https://www.youtube.com/watch?v=dQw4w9WgXc@",
        "https://www.youtube.com/shorts/tooShortId",
        "https://www.youtube.com/embed/wayTooLongId12345",
        "https://www.youtube.com/live/invalid*char",
        "https://youtu.be/inv@lidChar",
        "https://youtu.be/1234567890",
        "https://youtu.be/123456789012",
    ],
)
def test_parse_youtube_url_invalid_ids(invalid_id_url: str) -> None:
    with pytest.raises(InvalidURLError) as exc_info:
        parse_youtube_url(invalid_id_url)
    assert exc_info.value.code == ErrorCode.INVALID_URL


# -----------------------------------------------------------------------------
# Missing Video ID / Malformed Path Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_id_url",
    [
        "https://www.youtube.com",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/watch?v=",
        "https://www.youtube.com/watch?t=42",
        "https://www.youtube.com/shorts",
        "https://www.youtube.com/shorts/",
        "https://www.youtube.com/embed",
        "https://www.youtube.com/embed/",
        "https://www.youtube.com/live",
        "https://www.youtube.com/live/",
        "https://youtu.be",
        "https://youtu.be/",
        "https://www.youtube.com/feed/subscriptions",
        "https://www.youtube.com/channel/UC1234567890",
    ],
)
def test_parse_youtube_url_missing_ids(missing_id_url: str) -> None:
    with pytest.raises(InvalidURLError) as exc_info:
        parse_youtube_url(missing_id_url)
    assert exc_info.value.code == ErrorCode.INVALID_URL


# -----------------------------------------------------------------------------
# Empty and Non-String Inputs
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "empty_input",
    [
        "",
        "   ",
        "\t\n",
    ],
)
def test_parse_youtube_url_empty(empty_input: str) -> None:
    with pytest.raises(InvalidURLError) as exc_info:
        parse_youtube_url(empty_input)
    assert "cannot be empty" in str(exc_info.value)
    assert exc_info.value.code == ErrorCode.INVALID_URL


def test_parse_youtube_url_non_string() -> None:
    with pytest.raises(InvalidURLError) as exc_info:
        parse_youtube_url(12345)  # type: ignore[arg-type]
    assert "must be a string" in str(exc_info.value)
    assert exc_info.value.code == ErrorCode.INVALID_URL


# -----------------------------------------------------------------------------
# Exception Attributes & Default Message
# -----------------------------------------------------------------------------


def test_invalid_url_error_defaults() -> None:
    err = InvalidURLError()
    assert err.code == ErrorCode.INVALID_URL
    assert isinstance(err, ValueError)
    assert str(err) == "Please paste a valid YouTube link."
