from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.metadata import VideoMetadata, fetch_metadata


def test_video_metadata_dataclass():
    meta = VideoMetadata(title="Sample Title", channel="Sample Channel")
    assert meta.title == "Sample Title"
    assert meta.channel == "Sample Channel"


@pytest.mark.asyncio
async def test_fetch_metadata_success_primary():
    mock_response = httpx.Response(
        200,
        json={"title": "Introduction to AI", "author_name": "Stanford Online"},
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("dQw4w9WgXcQ")

    assert result.title == "Introduction to AI"
    assert result.channel == "Stanford Online"
    assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_metadata_fallback_secondary():
    def get_side_effect(url: str, **kwargs):
        if "noembed" in url:
            return httpx.Response(500, text="Service Unavailable")
        return httpx.Response(
            200,
            json={"title": "Deep Learning Specialization", "author_name": "DeepLearningAI"},
        )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = get_side_effect
        result = await fetch_metadata("dQw4w9WgXcQ")

    assert result.title == "Deep Learning Specialization"
    assert result.channel == "DeepLearningAI"
    assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_metadata_404_error():
    mock_response = httpx.Response(404, text="Not Found")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("unknown_vid")

    assert result.title == "Video (unknown_vid)"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_500_error():
    mock_response = httpx.Response(500, text="Internal Server Error")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("err_vid_500")

    assert result.title == "Video (err_vid_500)"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_timeout_exception():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")
        result = await fetch_metadata("timeout_vid", timeout_s=2.0)

    assert result.title == "Video (timeout_vid)"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_network_error():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        result = await fetch_metadata("net_err_vid")

    assert result.title == "Video (net_err_vid)"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_json_with_error_key():
    mock_response = httpx.Response(
        200,
        json={"error": "404 Not Found"},
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("err_key_vid")

    assert result.title == "Video (err_key_vid)"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_invalid_json():
    mock_response = httpx.Response(200, text="not valid json <html/>")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("bad_json_vid")

    assert result.title == "Video (bad_json_vid)"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_partial_fields():
    mock_response = httpx.Response(
        200,
        json={"title": "Only Title Available"},
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("partial_vid")

    assert result.title == "Only Title Available"
    assert result.channel == "YouTube Creator"


@pytest.mark.asyncio
async def test_fetch_metadata_custom_client():
    mock_response = httpx.Response(
        200,
        json={"title": "Custom Client Video", "author_name": "Custom Channel"},
    )
    custom_client = httpx.AsyncClient()
    with patch.object(custom_client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await fetch_metadata("custom_vid", client=custom_client)
        await custom_client.aclose()

    assert result.title == "Custom Client Video"
    assert result.channel == "Custom Channel"
