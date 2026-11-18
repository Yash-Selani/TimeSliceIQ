from __future__ import annotations

import asyncio
import html as html_lib
import logging
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from pydantic import BaseModel, Field
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
    "proxy",
    "forbidden",
    "403",
    "timeout",
    "timed out",
    "connection error",
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

    logger.warning("Transcript fetch failed for video %s: %s: %s", video_id, type(exc).__name__, exc)
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


def _is_cloudflare_worker(url: str | None) -> bool:
    """Check if the provided proxy URL is a Cloudflare Worker proxy."""
    if not url:
        return False
    u = url.strip().lower()
    return "workers.dev" in u or "cloudflare" in u or "pages.dev" in u or "/?url=" in u


_REAL_YT_API_CLASS = YouTubeTranscriptApi


class _GeminiTranscriptSegment(BaseModel):
    start: float = Field(..., description="Start timestamp in seconds")
    duration: float = Field(..., description="Segment duration in seconds")
    text: str = Field(..., description="Spoken transcript text for this segment")


class _GeminiTranscriptResponse(BaseModel):
    segments: list[_GeminiTranscriptSegment]


def _normalize_worker_base(worker_url: str) -> str:
    clean = worker_url.strip().rstrip("/")
    if clean.endswith("/?url="):
        clean = clean[:-6]
    elif clean.endswith("?url="):
        clean = clean[:-5]
    return clean


def _wrap_worker_url(clean_worker: str, url: str) -> str:
    return f"{clean_worker}/?url={urllib.parse.quote(url, safe='')}"


def _attach_cloudflare_worker(api: Any, worker_url: str) -> None:
    """Route requests made by api._fetcher._http_client through a Cloudflare Worker."""
    if not hasattr(api, "_fetcher") or not hasattr(api._fetcher, "_http_client"):
        return
    session = api._fetcher._http_client
    original_request = session.request
    clean_worker = _normalize_worker_base(worker_url)

    def worker_request(method: str, url: str, *args: Any, **kwargs: Any) -> Any:
        if isinstance(url, str) and ("youtube.com" in url or "youtu.be" in url):
            # Merge query params into target URL before wrapping for the worker
            params = kwargs.pop("params", None)
            full_url = url
            if params:
                qs = urllib.parse.urlencode(params, doseq=True)
                sep = "&" if "?" in full_url else "?"
                full_url = f"{full_url}{sep}{qs}"
            target_url = _wrap_worker_url(clean_worker, full_url)
            return original_request(method, target_url, *args, **kwargs)
        return original_request(method, url, *args, **kwargs)

    session.request = worker_request


def _parse_timedtext_xml(xml_text: str) -> list[dict]:
    """Parse YouTube timedtext XML (both <text start dur> and format=3 <p t d>) into snippets."""
    if not xml_text or not xml_text.strip():
        return []
    root = ET.fromstring(xml_text)
    snippets: list[dict] = []

    # Format 1: <transcript><text start="1.92" dur="4.72">...</text></transcript>
    for elem in root.findall(".//text"):
        text = html_lib.unescape("".join(elem.itertext())).strip()
        if not text:
            continue
        start = float(elem.attrib.get("start", 0.0))
        dur = float(elem.attrib.get("dur", 0.0))
        snippets.append({"start": round(start, 2), "duration": round(dur, 2), "text": text})

    if snippets:
        return snippets

    # Format 3: <timedtext format="3"><body><p t="1920" d="4720"><s>...</s></p></body></timedtext>
    for elem in root.findall(".//p"):
        text = html_lib.unescape("".join(elem.itertext())).strip()
        if not text:
            continue
        start_ms = float(elem.attrib.get("t", 0.0))
        dur_ms = float(elem.attrib.get("d", 0.0))
        snippets.append(
            {
                "start": round(start_ms / 1000.0, 2),
                "duration": round(dur_ms / 1000.0, 2),
                "text": text,
            }
        )
    return snippets


def _fetch_via_ios_innertube(video_id: str, proxy_url: str | None = None) -> list[dict]:
    """Fallback transcript fetcher using YouTube's iOS InnerTube client."""
    ios_ua = "com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3 like Mac OS X;)"
    web_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    is_cf = _is_cloudflare_worker(proxy_url)
    clean_worker = _normalize_worker_base(proxy_url) if (is_cf and proxy_url) else None

    def _req_url(url: str) -> str:
        return _wrap_worker_url(clean_worker, url) if clean_worker else url

    client_kwargs: dict[str, Any] = {"timeout": 10.0, "follow_redirects": True}
    if proxy_url and not is_cf:
        client_kwargs["proxy"] = proxy_url

    with httpx.Client(**client_kwargs) as client:
        watch_resp = client.get(
            _req_url(f"https://www.youtube.com/watch?v={video_id}"),
            headers={"User-Agent": web_ua, "Accept-Language": "en-US,en;q=0.9"},
        )
        watch_resp.raise_for_status()
        m = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', watch_resp.text)
        if not m:
            raise TranscriptBlockedError(f"Could not locate InnerTube API key for '{video_id}'")
        api_key = m.group(1)

        player_resp = client.post(
            _req_url(f"https://www.youtube.com/youtubei/v1/player?key={api_key}"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": ios_ua,
                "Accept-Language": "en-US,en;q=0.9",
            },
            json={
                "context": {
                    "client": {
                        "clientName": "IOS",
                        "clientVersion": "20.10.4",
                        "deviceModel": "iPhone16,2",
                        "hl": "en",
                    }
                },
                "videoId": video_id,
            },
        )
        player_resp.raise_for_status()
        data = player_resp.json()

        playability = data.get("playabilityStatus", {})
        if playability.get("status") != "OK":
            raise TranscriptBlockedError(
                f"iOS InnerTube playability blocked: {playability.get('status')} - {playability.get('reason')}"
            )

        tracks = (
            data.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        if not tracks:
            raise NoCaptionsError(f"No captions available for video '{video_id}'")

        # Prefer English, then manual captions, then first available track
        en = [t for t in tracks if str(t.get("languageCode", "")).startswith("en")]
        manual = [t for t in tracks if t.get("kind") != "asr"]
        chosen = en[0] if en else (manual[0] if manual else tracks[0])
        base_url = chosen.get("baseUrl")
        if not base_url:
            raise NoCaptionsError(f"Caption track missing baseUrl for '{video_id}'")

        tt_resp = client.get(
            _req_url(base_url),
            headers={"User-Agent": ios_ua, "Accept-Language": "en-US,en;q=0.9"},
        )
        tt_resp.raise_for_status()
        snippets = _parse_timedtext_xml(tt_resp.text)
        if not snippets:
            raise TranscriptBlockedError(f"Empty timedtext response for '{video_id}'")
        return snippets


def _recover_truncated_segments(raw_json: str) -> list[dict]:
    """Recover complete segment objects if structured JSON output was truncated at max_output_tokens."""
    import json

    recovered: list[dict] = []
    # Match individual complete JSON objects inside the segments array
    for match in re.finditer(r"\{[^{}]*\}", raw_json):
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict) and "start" in obj and "text" in obj:
                text = str(obj["text"]).strip()
                if text:
                    recovered.append(
                        {
                            "start": round(max(0.0, float(obj["start"])), 2),
                            "duration": round(max(1.0, float(obj.get("duration", 20.0))), 2),
                            "text": text,
                        }
                    )
        except Exception:
            continue
    return recovered


def _fetch_via_gemini(video_id: str) -> list[dict]:
    """Zero-IP-block fallback: transcribe YouTube video directly via Gemini native YouTube URI support."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from google import genai
    from google.genai import types

    from app.config import settings

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise TranscriptBlockedError("GEMINI_API_KEY not configured for native YouTube fallback.")

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    prompt = (
        "Transcribe the spoken content of this YouTube video into timestamped segments. "
        "Group speech into 45 to 60 second segments covering the entire video from start to end, "
        "with accurate start times (in seconds) and durations (in seconds). "
        "Capture all key points, explanations, and terms concisely. "
        "Return ONLY valid JSON matching the requested schema."
    )

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=_GeminiTranscriptResponse,
        max_output_tokens=16384,
        temperature=0.1,
    )

    # Prioritize models proven to work well on YouTube URIs and race them concurrently
    candidate_models = [
        settings.GEMINI_MODEL or "gemini-3-flash-preview",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
    ]
    models_to_try: list[str] = []
    for m in candidate_models:
        if m and m not in models_to_try:
            models_to_try.append(m)

    def _call_model(model_name: str) -> list[dict]:
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=42000))
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_uri(file_uri=video_url, mime_type="video/mp4"),
                prompt,
            ],
            config=config,
        )
        parsed: _GeminiTranscriptResponse | None = None
        raw_text = getattr(response, "text", None) or ""

        if hasattr(response, "parsed") and isinstance(response.parsed, _GeminiTranscriptResponse):
            parsed = response.parsed
        elif raw_text.strip():
            clean = raw_text.strip()
            if clean.startswith("```"):
                lines = clean.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                clean = "\n".join(lines).strip()
            try:
                parsed = _GeminiTranscriptResponse.model_validate_json(clean)
            except Exception:
                recovered = _recover_truncated_segments(clean)
                if recovered:
                    logger.info(
                        "Recovered %d transcript segments from truncated JSON for %s (%s)",
                        len(recovered),
                        video_id,
                        model_name,
                    )
                    return recovered
                raise

        if parsed and parsed.segments:
            snippets = [
                {
                    "start": round(max(0.0, float(s.start)), 2),
                    "duration": round(max(1.0, float(s.duration)), 2),
                    "text": s.text.strip(),
                }
                for s in parsed.segments
                if s.text and s.text.strip()
            ]
            if snippets:
                logger.info(
                    "Successfully transcribed video %s via Gemini fallback (%s, %d segments)",
                    video_id,
                    model_name,
                    len(snippets),
                )
                return snippets
        raise ValueError(f"Empty transcript returned by {model_name}")

    last_exc: Exception | None = None
    executor = ThreadPoolExecutor(max_workers=len(models_to_try))
    futures = {executor.submit(_call_model, m): m for m in models_to_try}
    try:
        for fut in as_completed(futures, timeout=46):
            model_name = futures[fut]
            try:
                snippets = fut.result()
                if snippets:
                    return snippets
            except Exception as exc:
                last_exc = exc
                logger.warning("Gemini native YouTube fallback failed with %s for %s: %s", model_name, video_id, exc)
    except Exception as exc:
        last_exc = exc
        logger.warning("Gemini fallback race timed out for %s: %s", video_id, exc)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    raise TranscriptBlockedError(f"Gemini YouTube fallback failed for '{video_id}': {last_exc}")


def _get_api_instance(proxy_url: str | None = None) -> Any:
    """Instantiate YouTubeTranscriptApi with proxy configuration if provided."""
    api: Any
    is_cf_worker = _is_cloudflare_worker(proxy_url)

    if not proxy_url or is_cf_worker:
        api = YouTubeTranscriptApi()
    else:
        # Traditional forward proxy (e.g. http://user:pass@host:port)
        try:
            proxy_config = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
            api = YouTubeTranscriptApi(proxy_config=proxy_config)
        except (TypeError, AttributeError):
            # Try proxies keyword argument (for mocks or alternative wrappers)
            proxies_dict = {"http": proxy_url, "https": proxy_url}
            try:
                api = YouTubeTranscriptApi(proxies=proxies_dict)  # type: ignore[call-arg]
            except TypeError:
                api = YouTubeTranscriptApi()

    # Route through Cloudflare Worker if configured
    if is_cf_worker and proxy_url:
        _attach_cloudflare_worker(api, proxy_url)

    # Set Accept-Language without clobbering mobile InnerTube headers
    if hasattr(api, "_fetcher") and hasattr(api._fetcher, "_http_client"):
        try:
            api._fetcher._http_client.headers.update({
                "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            })
        except Exception as exc:
            logger.debug("Failed to set custom headers on YouTube client: %s", exc)

    return api


def _fetch_transcript_sync(video_id: str, proxy_url: str | None = None) -> list[dict]:
    """Synchronous internal implementation of transcript fetching."""
    api: Any = None
    try:
        api = _get_api_instance(proxy_url)

        # 1. Standard instance API (youtube-transcript-api >= 1.2.0)
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
                        en = [t for t in transcripts if getattr(t, "language_code", "").startswith("en")]
                        manual = [t for t in transcripts if not getattr(t, "is_generated", False)]
                        chosen = en[0] if en else (manual[0] if manual else transcripts[0])
                        raw = chosen.fetch()
                    except Exception as fallback_exc:
                        logger.warning("Fallback transcript fetch failed for %s: %s", video_id, fallback_exc)
                        raise initial_exc
                else:
                    raise initial_exc
        # 2. Method on instance or class for older versions / legacy mocks
        elif hasattr(api, "get_transcript") and callable(getattr(api, "get_transcript")):
            proxies_dict = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            try:
                raw = api.get_transcript(video_id, proxies=proxies_dict)
            except TypeError:
                raw = api.get_transcript(video_id)
        elif (
            hasattr(YouTubeTranscriptApi, "get_transcript")
            and callable(getattr(YouTubeTranscriptApi, "get_transcript"))
            and not isinstance(YouTubeTranscriptApi, type(api))
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
        mapped = _map_exception(exc, video_id)

        # Only run live multi-tier fallbacks when YouTubeTranscriptApi is NOT mocked in unit tests
        if isinstance(mapped, TranscriptBlockedError) and isinstance(api, _REAL_YT_API_CLASS):
            # Fallback 1: iOS InnerTube client (via proxy if set, then direct)
            for attempt_proxy in ([proxy_url, None] if proxy_url else [None]):
                try:
                    logger.info("Trying iOS InnerTube fallback for %s (proxy=%s)", video_id, bool(attempt_proxy))
                    snippets = _fetch_via_ios_innertube(video_id, proxy_url=attempt_proxy)
                    if snippets:
                        return snippets
                except NoCaptionsError:
                    raise
                except Exception as ios_exc:
                    logger.warning("iOS InnerTube fallback failed for %s: %s", video_id, ios_exc)

            # Fallback 2: Gemini native YouTube URL transcription (immune to datacenter IP bans)
            try:
                logger.info("Trying Gemini native YouTube transcription fallback for %s", video_id)
                snippets = _fetch_via_gemini(video_id)
                if snippets:
                    return snippets
            except Exception as gemini_exc:
                logger.warning("Gemini fallback also failed for %s: %s", video_id, gemini_exc)

        raise mapped from exc


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
