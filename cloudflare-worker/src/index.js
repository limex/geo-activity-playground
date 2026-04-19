// Proxies Mapbox raster tiles and injects the access token server-side.
// URL shape: /:style/:size/:z/:x/:y.png
// The Mapbox username and token are Worker secrets (MAPBOX_USERNAME, MAPBOX_TOKEN).

const PATH_RE = /^\/([A-Za-z0-9_-]+)\/(256|512)\/(\d{1,2})\/(\d+)\/(\d+)\.png$/;

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const url = new URL(request.url);
    const match = PATH_RE.exec(url.pathname);
    if (!match) {
      return new Response("Not Found", { status: 404 });
    }
    const [, style, size, z, x, y] = match;

    const zoom = parseInt(z, 10);
    if (zoom < 0 || zoom > 22) {
      return new Response("Invalid zoom", { status: 400 });
    }

    const cache = caches.default;
    // Use a canonical cache key derived from the request URL so the hostname
    // is not hardcoded in source. url.origin reflects whatever host the
    // Worker is bound to.
    const cacheKey = new Request(`${url.origin}/${style}/${size}/${z}/${x}/${y}.png`, { method: "GET" });

    let cached = await cache.match(cacheKey);
    if (cached) {
      return withCors(cached);
    }

    const upstream = new URL(
      `https://api.mapbox.com/styles/v1/${env.MAPBOX_USERNAME}/${style}/tiles/${size}/${z}/${x}/${y}`
    );
    upstream.searchParams.set("access_token", env.MAPBOX_TOKEN);

    const upstreamRes = await fetch(upstream.toString(), {
      method: "GET",
      headers: { "Accept": "image/png,image/*;q=0.8,*/*;q=0.5" },
      cf: { cacheEverything: true, cacheTtl: 2592000 },
    });

    if (!upstreamRes.ok) {
      return new Response(`Upstream error: ${upstreamRes.status}`, { status: upstreamRes.status });
    }

    const headers = new Headers(upstreamRes.headers);
    headers.set("Cache-Control", "public, max-age=2592000, immutable");
    headers.delete("Set-Cookie");

    const response = new Response(upstreamRes.body, {
      status: upstreamRes.status,
      headers,
    });

    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return withCors(response);
  },
};

function withCors(response) {
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  return new Response(response.body, { status: response.status, headers });
}
