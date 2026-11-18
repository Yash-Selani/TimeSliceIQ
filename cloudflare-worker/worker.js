/**
 * TimeSliceIQ - Cloudflare Worker YouTube Proxy
 *
 * Proxies YouTube watch HTML, InnerTube JSON API (/youtubei/v1/player),
 * and timedtext caption endpoints from Cloudflare's edge network while
 * preserving POST Content-Type/body and method-appropriate headers.
 */

export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const requestUrl = new URL(request.url);
    const targetUrl = requestUrl.searchParams.get("url");

    if (!targetUrl) {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "TimeSliceIQ YouTube Proxy Worker",
          usage: "/?url=https://www.youtube.com/watch?v=VIDEO_ID",
        }),
        {
          status: 200,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    let parsedTarget;
    try {
      parsedTarget = new URL(targetUrl);
    } catch {
      return new Response("Invalid target URL", { status: 400, headers: corsHeaders });
    }

    const host = parsedTarget.hostname.toLowerCase();
    const isYouTube =
      host === "www.youtube.com" ||
      host === "youtube.com" ||
      host === "m.youtube.com" ||
      host === "youtu.be" ||
      host === "youtube-nocookie.com" ||
      host === "www.youtube-nocookie.com";

    if (!isYouTube) {
      return new Response("Target must be a YouTube URL", { status: 403, headers: corsHeaders });
    }

    const isPost = request.method === "POST";
    const headers = new Headers();

    // Preserve incoming User-Agent if caller provided a mobile/InnerTube UA, else default to Chrome
    const incomingUA = request.headers.get("user-agent");
    if (incomingUA && !incomingUA.toLowerCase().includes("python-requests")) {
      headers.set("User-Agent", incomingUA);
    } else {
      headers.set(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
      );
    }

    headers.set("Accept-Language", request.headers.get("accept-language") || "en-US,en;q=0.9");

    if (isPost) {
      // Preserve JSON Content-Type and API headers for /youtubei/v1/player POST requests
      headers.set("Content-Type", request.headers.get("content-type") || "application/json");
      headers.set("Accept", "application/json, */*");
      headers.set("Origin", "https://www.youtube.com");
      headers.set("Referer", "https://www.youtube.com/");
      const clientName = request.headers.get("x-youtube-client-name");
      const clientVersion = request.headers.get("x-youtube-client-version");
      if (clientName) headers.set("X-YouTube-Client-Name", clientName);
      if (clientVersion) headers.set("X-YouTube-Client-Version", clientVersion);
    } else {
      headers.set(
        "Accept",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
      );
      headers.set("Sec-Fetch-Mode", "navigate");
      headers.set("Sec-Fetch-Site", "none");
      headers.set("Sec-Fetch-Dest", "document");
    }

    const incomingCookie = request.headers.get("cookie");
    if (incomingCookie) {
      headers.set("cookie", incomingCookie);
    }

    try {
      const fetchInit = {
        method: request.method,
        headers,
        redirect: "follow",
      };

      if (request.method !== "GET" && request.method !== "HEAD") {
        fetchInit.body = await request.arrayBuffer();
      }

      const response = await fetch(targetUrl, fetchInit);
      const body = await response.arrayBuffer();

      const responseHeaders = new Headers(response.headers);
      // Remove encoding/length headers since fetch() already decoded the body
      responseHeaders.delete("content-encoding");
      responseHeaders.delete("content-length");
      responseHeaders.set("Access-Control-Allow-Origin", "*");
      responseHeaders.set("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS");
      responseHeaders.set("Access-Control-Allow-Headers", "*");

      return new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: String(err) }), {
        status: 502,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  },
};
