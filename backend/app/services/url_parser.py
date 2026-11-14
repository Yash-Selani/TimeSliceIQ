from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from app.schemas import ERROR_MESSAGES, ErrorCode

ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtube-nocookie.com",
    }
)

VIDEO_ID_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_\-]{11}$")


class InvalidURLError(ValueError):
    """Raised when a YouTube URL is invalid, unsupported, or has an invalid video ID."""

    def __init__(
        self,
        message: str = ERROR_MESSAGES[ErrorCode.INVALID_URL],
        code: ErrorCode = ErrorCode.INVALID_URL,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def parse_youtube_url(url: str) -> str:
    """Extract and validate the 11-character YouTube video ID from a URL.

    Supported YouTube URL formats:
      - Standard watch URLs: https://www.youtube.com/watch?v=ID (including timestamps, extra params)
      - Mobile URLs: https://m.youtube.com/watch?v=ID
      - Short URLs: https://youtu.be/ID (query params stripped)
      - Shorts: https://www.youtube.com/shorts/ID
      - Embeds: https://www.youtube.com/embed/ID
      - Privacy-enhanced embeds: https://www.youtube-nocookie.com/embed/ID
      - Live streams: https://www.youtube.com/live/ID
      - Root with query: https://www.youtube.com/?v=ID
      - Protocol-relative or schemeless URLs: youtube.com/watch?v=ID

    Supported hosts:
      - youtube.com
      - www.youtube.com
      - m.youtube.com
      - youtu.be
      - www.youtube-nocookie.com

    Args:
        url: The YouTube URL string to parse.

    Returns:
        The validated 11-character video ID.

    Raises:
        InvalidURLError: If the URL is empty, non-string, uses an invalid scheme,
                         points to an unallowed domain, contains no video ID,
                         or has an invalid video ID format.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL must be a string.")

    cleaned_url = url.strip()
    if not cleaned_url:
        raise InvalidURLError("URL cannot be empty.")

    try:
        parsed = urlparse(cleaned_url)
    except Exception as exc:
        raise InvalidURLError(f"Failed to parse URL: {exc}") from exc

    if parsed.scheme:
        if parsed.scheme.lower() not in ("http", "https"):
            raise InvalidURLError(
                f"Unsupported URL scheme: '{parsed.scheme}'. Only HTTP and HTTPS are allowed."
            )
    else:
        # Prepend https scheme for schemeless URLs (e.g. www.youtube.com/watch?v=...)
        if cleaned_url.startswith("//"):
            cleaned_url = "https:" + cleaned_url
        else:
            cleaned_url = "https://" + cleaned_url
        try:
            parsed = urlparse(cleaned_url)
        except Exception as exc:
            raise InvalidURLError(f"Failed to parse URL: {exc}") from exc

    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLError("URL missing valid hostname.")

    hostname = hostname.lower()
    if hostname not in ALLOWED_HOSTS:
        raise InvalidURLError(f"Host '{hostname}' is not an allowed YouTube domain.")

    path_segments = [seg for seg in parsed.path.split("/") if seg]
    query_params = parse_qs(parsed.query)

    video_id: str | None = None

    if hostname == "youtu.be":
        # youtu.be/ID or youtu.be/ID?si=xxx (trailing slashes stripped by split)
        if len(path_segments) == 1:
            video_id = path_segments[0]
        elif len(path_segments) == 2 and path_segments[0].lower() in ("shorts", "embed", "live"):
            video_id = path_segments[1]
    else:
        # youtube.com, www.youtube.com, m.youtube.com, www.youtube-nocookie.com
        if path_segments:
            first_seg = path_segments[0].lower()
            if first_seg in ("shorts", "embed", "live", "v") and len(path_segments) == 2:
                video_id = path_segments[1]
            elif first_seg == "watch":
                v_vals = query_params.get("v")
                if v_vals and v_vals[0]:
                    video_id = v_vals[0]
            elif "v" in query_params and query_params["v"] and query_params["v"][0]:
                video_id = query_params["v"][0]
        else:
            # e.g. https://www.youtube.com/?v=ID
            v_vals = query_params.get("v")
            if v_vals and v_vals[0]:
                video_id = v_vals[0]

    if not video_id:
        raise InvalidURLError("No video ID found in URL.")

    if not VIDEO_ID_PATTERN.match(video_id):
        raise InvalidURLError(
            f"Invalid video ID format '{video_id}'. "
            "YouTube video IDs must match '^[a-zA-Z0-9_-]{11}$'."
        )

    return video_id
