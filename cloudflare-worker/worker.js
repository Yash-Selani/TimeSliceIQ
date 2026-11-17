/**
 * TimeSliceIQ - Cloudflare Worker YouTube Proxy
 *
 * This lightweight Cloudflare Worker intercepts requests to YouTube
 * (watch HTML and timedtext caption endpoints) and fetches them from
 * Cloudflare's global edge network with clean browser headers,
 * bypassing AWS/Vercel datacenter IP rate limits.
 */

export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const requestUrl = new URL(request.url);
    const targetUrl = requestUrl.searchParams.get("url");

    // Health check endpoint
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

    // Validate that the target is a YouTube URL for security
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

    // Set standard browser headers to avoid automated scraping detection
    const headers = new Headers();
    headers.set(
      "User-Agent",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    );
    headers.set("Accept-Language", "en-US,en;q=0.9,hi;q=0.8");
    headers.set(
      "Accept",
      "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    );
    headers.set("Sec-Fetch-Mode", "navigate");
    headers.set("Sec-Fetch-Site", "none");
    headers.set("Sec-Fetch-Dest", "document");

    // Forward any incoming cookies or headers from client session if present
    const incomingCookie = request.headers.get("cookie");
    if (incomingCookie) {
      headers.set("cookie", incomingCookie);
    }

    try {
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
        redirect: "follow",
      });

      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("Access-Control-Allow-Origin", "*");
      responseHeaders.set("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS");
      responseHeaders.set("Access-Control-Allow-Headers", "*");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: "Fetch failed", details: String(err) }),
        { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
  },
};
