from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NOEMBED_URL_TEMPLATE = "https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
YOUTUBE_OEMBED_URL_TEMPLATE = (
    "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
)
DEFAULT_CHANNEL = "YouTube Creator"


@dataclass
class VideoMetadata:
    title: str
    channel: str


async def _fetch_from_endpoints(
    client: httpx.AsyncClient,
    video_id: str,
    endpoints: list[str],
    fallback: VideoMetadata,
) -> VideoMetadata | None:
    for url in endpoints:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                try:
                    data: Any = response.json()
                except Exception:
                    logger.warning("Failed to decode JSON from %s", url)
                    continue

                if isinstance(data, dict) and "error" not in data:
                    raw_title = data.get("title")
                    raw_channel = data.get("author_name")
                    title = str(raw_title).strip() if raw_title else None
                    channel = str(raw_channel).strip() if raw_channel else None
                    if title or channel:
                        return VideoMetadata(
                            title=title or fallback.title,
                            channel=channel or fallback.channel,
                        )
            else:
                logger.warning(
                    "Metadata endpoint %s returned status %d for video %s",
                    url,
                    response.status_code,
                    video_id,
                )
        except httpx.HTTPError as exc:
            logger.warning("HTTP error requesting metadata from %s: %s", url, exc)
        except Exception as exc:
            logger.warning("Unexpected error requesting metadata from %s: %s", url, exc)
    return None


async def fetch_metadata(
    video_id: str,
    timeout_s: float = 8.0,
    client: httpx.AsyncClient | None = None,
) -> VideoMetadata:
    """Fetch video metadata (title and channel) using YouTube oEmbed endpoints.

    Falls back gracefully to placeholder metadata if requests fail, time out,
    or return non-200 responses.
    """
    clean_video_id = video_id.strip()
    fallback = VideoMetadata(
        title=f"Video ({clean_video_id})",
        channel=DEFAULT_CHANNEL,
    )

    endpoints = [
        NOEMBED_URL_TEMPLATE.format(video_id=clean_video_id),
        YOUTUBE_OEMBED_URL_TEMPLATE.format(video_id=clean_video_id),
    ]

    try:
        if client is not None:
            result = await _fetch_from_endpoints(client, clean_video_id, endpoints, fallback)
            if result is not None:
                return result
        else:
            async with httpx.AsyncClient(timeout=timeout_s) as ac:
                result = await _fetch_from_endpoints(ac, clean_video_id, endpoints, fallback)
                if result is not None:
                    return result
    except Exception as exc:
        logger.warning("Error fetching metadata for video_id %s: %s", clean_video_id, exc)

    return fallback
