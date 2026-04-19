# tiles-mapbox Cloudflare Worker

Proxies Mapbox raster tiles through a Cloudflare Worker, injecting the access
token server-side so it is never sent to the browser.

## URL shape

```
https://<your-worker-host>/{style}/{size}/{z}/{x}/{y}.png
```

`{size}` must be `256` or `512`.

## Setup

```bash
cd cloudflare-worker
cp wrangler.toml.example wrangler.toml
# Edit wrangler.toml: set the route pattern and zone_name to your domain.
# wrangler.toml is gitignored so the hostname never ends up in the repo.

npx wrangler@latest login
npx wrangler@latest secret put MAPBOX_USERNAME   # e.g. your Mapbox account name
npx wrangler@latest secret put MAPBOX_TOKEN      # a pk.* token
npx wrangler@latest deploy
```

Add a DNS record for the Worker hostname in the Cloudflare dashboard:
- Type `AAAA`, Name `<your-subdomain>`, address `100::`, Proxy status **Proxied**.

Then paste the tile URL template into the app's Settings → Maps → Map tile URL.

## Caching

- Cloudflare edge cache: 30 days (`Cache-Control: public, max-age=2592000, immutable`).
- Upstream fetch uses `cf.cacheEverything` + `cacheTtl=2592000`.
