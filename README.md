# Geo Activity Playground

Geo Activity Playground is a software to view recorded outdoor activities and derive various insights from your data collection. All data is kept on your machine, hence it is suitable for people who have an affinity for data analysis and privacy.

It caters to serve a similar purpose as other systems like Strava, Statshunters or VeloViewer, though the focus here is on self-hosting and using local files.

One can use this program with a local collection of activity files (GPX, FIT, TCX, KML, CSV) or via the Strava API. The latter is appealing to people who want to keep their data with Strava primarily. In case that one wants to move, this might provide a noncommittal way of testing out this project.

The main user interface is web-based, you can run this on your Linux, Mac or Windows laptop. If you want, it can also run on a home server or your personal cloud instance.

Please see the [hosted documentation](https://martin-ueding.github.io/geo-activity-playground/) for more details, setup instructions and a general tour of the available features.

---

## Fork Changes (v1.26.8)

- **Map tile cache: clear via UI**: A new "Map Tile Cache" card in Settings → Maintenance lets you delete all cached OSM tiles with one click. Useful when tiles look outdated or to reclaim disk space — tiles are re-downloaded on demand.
- **Photo thumbnail quality**: WebP thumbnails are now saved at quality=95 (previously Pillow default ~80), preserving more detail in map markers and photo previews.

---

## Fork Changes (v1.26.7)

- **Standalone photo import**: Photos without a matching activity can now be imported when "Import Standalone Photos" is enabled in Settings → Misc. Photos with GPS coordinates but no EXIF timestamp are also accepted under this mode. When the setting is off, unmatched photos are skipped and stay in the upload folder for review — enabling the setting is a deliberate choice to show those photos on the map linked to their GPS position alone.
- **Configurable map tile styles**: The color transform applied to map tiles (color, pastel, grayscale, etc.) is now configurable per map type in Settings → Tile Source. Three groups can be set independently: standard maps (home, photo map, search, segments), activity detail maps, and track overlay maps (lines, names, day view). Defaults are unchanged.

---

## Fork Changes (v1.26.6)

- **Photo map: activity link**: Clicking the photo popup on the photo map now shows the activity ID as a badge in the top-left corner, linking to the activity page (opens in new tab).
- **Photo map: popup sizing fixed**: Photo popups now correctly size their frame on first open (previously required reopening the popup to render correctly). Fixed on both the global photo map and individual activity pages.
- **GPS hemisphere bug fixed**: Photos taken west of Greenwich or south of the equator were stored with incorrect (positive) coordinates. EXIF `GPSLongitudeRef`/`GPSLatitudeRef` tags are now respected, correctly negating coordinates for W/S hemispheres.

---

## Fork Changes (v1.26.5)

- **Photo bulk import**: Drop images into `photo-upload/` inside the playground directory and trigger import via the web UI (Upload Photos page). Imported photos are deleted from the folder automatically; unmatched ones stay for review.
- **Photo storage optimised**: Originals are deleted after import. Only two WebP thumbnails are kept per photo (128px for map markers, 512px for previews). No upscaling — images smaller than the target size are stored at their original dimensions.
- **Timezone-aware EXIF parsing**: When a photo lacks an EXIF timezone offset, the correct local timezone is inferred from GPS coordinates using `timezonefinder`. Fixes incorrect UTC mapping for cameras that store local time without offset.
- **Activity grace period**: Photos taken slightly before or after an activity can still be matched. Configurable in Settings → Management → Misc. (default: 10 minutes).
- **Duplicate detection**: Photos with an identical EXIF timestamp are skipped and deleted from the upload folder automatically.
- **Misc. settings page**: New Settings → Management → Misc. page for miscellaneous configuration values.

---

## Fork Changes (v1.26.4)

- **HTTP tile caching**: Heatmap tiles now return `Cache-Control: public, max-age=43200` (12 hours) and an `ETag` header. Browsers skip the download on unchanged tiles (304 Not Modified), reducing bandwidth on repeated map panning and zooming.
- **SQLite WAL mode**: Database now runs in Write-Ahead Logging mode with `synchronous=NORMAL`, improving concurrent read/write performance during tile serving.

---

## Fork Changes (v1.26.3)


- **Default-deny authentication**: All pages now require login when a password is configured. Previously only specific pages were protected via per-route decorators — any newly added page was public by default.
- **Tile endpoints remain public**: Background map tiles (`/tile/`), heatmap tiles (`/heatmap/tile/`) and explorer tiles (`/explorer/.../tile/`) are served without authentication so embedded maps work without a session.
- **Logout menu entry**: Added "Log Out" to the admin dropdown in the navigation bar.

---

## Fork Changes (v1.26.2)

This is a fork of [martin-ueding/geo-activity-playground](https://github.com/martin-ueding/geo-activity-playground). The following changes were made on top of v1.26.0:

- **Production WSGI server**: Replaced Werkzeug development server with [Waitress](https://docs.pylonsproject.org/projects/waitress/) (16 threads) for parallel tile serving
- **Dev/prod switch**: `GAP_DEV=1` environment variable enables Werkzeug with debugger; `GAP_DEV=0` (default) uses Waitress
- **Docker Compose**: Added `docker-compose.yml` with `container_name`, local image build (`pull_policy: never`), and `GAP_DEV` environment variable
- **Optimized Docker build**: Added `.dockerignore` to reduce build context from ~1GB to ~22KB; replaced `uv run` CMD with direct venv Python to prevent dev dependency installation at startup
- **Bug fix**: Fixed `KeyError: 'id'` crash on heatmap tile requests when search filters return no matching activities
- **Deploy script**: Added `deploy-to-prod.sh` for rsync-based deployment to a production server

---

## 🚀 Features

- 📍 **Activity Import & Analysis**  
  Use your GPX, FIT, TCX, KML, or CSV files. View detailed stats like distance, elevation and more.

- 🗺️ **Interactive Maps & Heatmaps**  
  Visualize routes on a map, create heatmaps of your most frequent paths, and spot your favorite spots or missed areas.

- 🧩 **Explorer Tiles**  
  Break the world into tiles and see which ones you’ve visited — great for motivation and adventure planning!

- 🛡️ **Privacy Zones**  
  Hide or blur sensitive areas like your home or workplace. Your data stays private and local.

- 🔁 **Strava API Integration (Optional)**  
  Import activities directly from your Strava account with a single click. No data is uploaded — it’s all stored locally.

---

## 📷 Screenshots

Here are a few examples of what Geo Activity Playground looks like in action:

### 🏃 Activity Detail View
![Activity Screenshot](https://martin-ueding.github.io/geo-activity-playground/images/screenshot-activity.png)

### 🔥 Heatmap View
![Heatmap Screenshot](https://martin-ueding.github.io/geo-activity-playground/images/screenshot-heatmap.png)

### 🧩 Explorer Tiles
![Explorer Screenshot](https://martin-ueding.github.io/geo-activity-playground/images/screenshot-explorer.png)

### 📊 Summary Dashboard
![Summary Screenshot](https://martin-ueding.github.io/geo-activity-playground/images/screenshot-summary.png)

---

## 🛠️ Installation

The app runs on **Linux**, **macOS**, and **Windows**. No cloud service required — it's just Python and a browser!

For full setup instructions and OS-specific steps, visit the [documentation](https://martin-ueding.github.io/geo-activity-playground/).

