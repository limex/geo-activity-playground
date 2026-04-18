import logging

import matplotlib.pylab as pl
import numpy as np
import sqlalchemy
from flask import Blueprint, Response, render_template, request
from PIL import Image, ImageDraw

from ...core.activities import ActivityRepository
from ...core.config import Config
from ...core.datamodel import DB, StoredSearchQuery
from ...core.heatmap_cache import blob_to_counts, get_tile_cache, write_tile_cache
from ...core.png_encode import rgba_float_to_png
from ...core.meta_search import (
    apply_search_filter,
    get_stored_queries,
    is_search_active,
    parse_search_params,
    primitives_to_jinja,
    primitives_to_json,
    primitives_to_url_str,
    register_search_query,
)
from ...core.raster_map import OSM_TILE_SIZE
from ...core.tiles import get_tile_upper_left_lat_lon
from ...explorer.tile_visits import TileVisitAccessor, get_tile_medians
from ..authenticator import Authenticator
from .explorer_blueprint import bounding_box_for_biggest_cluster

logger = logging.getLogger(__name__)


def make_heatmap_blueprint(
    repository: ActivityRepository,
    tile_visit_accessor: TileVisitAccessor,
    config: Config,
    authenticator: Authenticator,
) -> Blueprint:
    blueprint = Blueprint("heatmap", __name__, template_folder="templates")

    tile_evolution_states = tile_visit_accessor.tile_state["evolution_state"]
    activities_per_tile = tile_visit_accessor.tile_state["activities_per_tile"]

    @blueprint.route("/")
    def index():
        primitives = parse_search_params(request.args)

        if authenticator.is_authenticated():
            register_search_query(primitives)

        zoom = 14
        medians = get_tile_medians(zoom)
        median_lat, median_lon = get_tile_upper_left_lat_lon(
            medians[0], medians[1], zoom
        )
        cluster_state = tile_evolution_states[zoom]

        stored_queries = get_stored_queries()
        search_query_favorites = [
            (str(q), q.to_url_str()) for q in stored_queries if q.is_favorite
        ]
        search_query_last = [
            (str(q), q.to_url_str()) for q in stored_queries if not q.is_favorite
        ]

        context = {
            "center": {
                "latitude": median_lat,
                "longitude": median_lon,
                "bbox": (
                    bounding_box_for_biggest_cluster(
                        cluster_state.clusters.values(), zoom
                    )
                    if len(cluster_state.memberships) > 0
                    else {}
                ),
            },
            "extra_args": primitives_to_url_str(primitives),
            "query": primitives_to_jinja(primitives),
            "search_query_favorites": search_query_favorites,
            "search_query_last": search_query_last,
        }

        return render_template("heatmap/index.html.j2", **context)

    @blueprint.route("/tile/<int:z>/<int:x>/<int:y>.png")
    def tile(x: int, y: int, z: int):
        primitives = parse_search_params(request.args)
        png_bytes, num_activities = _get_tile_png(
            x, y, z, primitives, config, repository, activities_per_tile
        )
        etag = str(num_activities) if num_activities is not None else None
        headers: dict[str, str] = {
            "Cache-Control": "public, max-age=43200",
            "Access-Control-Allow-Origin": "*",
        }
        if etag:
            headers["ETag"] = etag
        if etag and request.headers.get("If-None-Match") == etag:
            return Response(status=304, headers=headers)
        return Response(png_bytes, mimetype="image/png", headers=headers)

    return blueprint


def _get_tile_png(
    x: int,
    y: int,
    z: int,
    primitives: dict,
    config: Config,
    repository: ActivityRepository,
    activities_per_tile: dict[int, dict[tuple[int, int], set[int]]],
) -> tuple[bytes, int | None]:
    tile_pixels = (OSM_TILE_SIZE, OSM_TILE_SIZE)
    tile_counts = np.zeros(tile_pixels, dtype=np.int32)
    activity_ids = activities_per_tile[z].get((x, y), set())

    search_query_id: int | None = None
    should_use_cache = True
    if is_search_active(primitives):
        activities = apply_search_filter(primitives)
        matching_activity_ids = set(activities["id"].tolist())
        activity_ids = activity_ids & matching_activity_ids
        search_query_id = _favorite_search_query_id(primitives)
        should_use_cache = search_query_id is not None

    if should_use_cache:
        parsed_activities: set[int] = set()
        cache_entry = get_tile_cache(
            zoom=z, tile_x=x, tile_y=y, search_query_id=search_query_id
        )
        if cache_entry:
            try:
                tile_counts = blob_to_counts(cache_entry.counts).astype(
                    np.int32, copy=False
                )
                if tile_counts.shape != tile_pixels:
                    raise ValueError("invalid tile shape in cache")
                parsed_activities = set(cache_entry.included_activity_ids or [])
            except ValueError:
                logger.warning(
                    f"Resetting corrupted heatmap cache for {x=}/{y=}/{z=}/{search_query_id=}."
                )
                tile_counts = np.zeros(tile_pixels, dtype=np.int32)
                parsed_activities = set()

            if (
                parsed_activities == activity_ids
                and cache_entry.png
            ):
                return cache_entry.png, len(parsed_activities)

        if parsed_activities - activity_ids:
            logger.warning(
                f"Resetting heatmap cache for {x=}/{y=}/{z=}/{search_query_id=} because activities have been removed."
            )
            tile_counts = np.zeros(tile_pixels, dtype=np.int32)
            parsed_activities.clear()

        for activity_id in activity_ids:
            if activity_id in parsed_activities:
                continue
            try:
                time_series = repository.get_time_series(activity_id)
            except ValueError:
                logger.warning(
                    f"Skipping deleted activity {activity_id} for {x=}/{y=}/{z=}."
                )
                continue
            parsed_activities.add(activity_id)
            _paint_activity(tile_counts, time_series, x=x, y=y, z=z)

        png_bytes = rgba_float_to_png(_counts_to_image(tile_counts, config))
        write_tile_cache(
            zoom=z,
            tile_x=x,
            tile_y=y,
            search_query_id=search_query_id,
            counts=tile_counts,
            included_activity_ids=parsed_activities,
            min_activities=config.heatmap_cache_min_activities,
            png=png_bytes,
        )
        return png_bytes, len(parsed_activities)
    else:
        for activity_id in activity_ids:
            try:
                time_series = repository.get_time_series(activity_id)
            except ValueError:
                logger.warning(
                    f"Skipping deleted activity {activity_id} for {x=}/{y=}/{z=}."
                )
                continue
            _paint_activity(tile_counts, time_series, x=x, y=y, z=z)
        return rgba_float_to_png(_counts_to_image(tile_counts, config)), None


def _favorite_search_query_id(primitives: dict) -> int | None:
    query_json = primitives_to_json(primitives)
    return DB.session.scalar(
        sqlalchemy.select(StoredSearchQuery.id).where(
            StoredSearchQuery.query_json == query_json,
            StoredSearchQuery.is_favorite.is_(True),
        )
    )


def _paint_activity(
    tile_counts: np.ndarray, time_series, *, x: int, y: int, z: int
) -> None:
    tile_pixels = (OSM_TILE_SIZE, OSM_TILE_SIZE)
    for _, group in time_series.groupby("segment_id"):
        xy_pixels = (
            np.array([group["x"] * 2**z - x, group["y"] * 2**z - y]).T * OSM_TILE_SIZE
        )
        im = Image.new("L", tile_pixels)
        draw = ImageDraw.Draw(im)
        pixels = list(map(int, xy_pixels.flatten()))
        draw.line(pixels, fill=1, width=max(3, 6 * (z - 17)))
        aim = np.array(im)
        tile_counts += aim


def _counts_to_image(counts: np.ndarray, config: Config) -> np.ndarray:
    tile_counts = np.zeros(counts.shape)
    tile_counts += counts
    tile_counts = np.sqrt(tile_counts) / 5
    tile_counts[tile_counts > 1.0] = 1.0
    cmap = pl.get_cmap(config.color_scheme_for_heatmap)
    data_color = cmap(tile_counts)
    data_color[tile_counts > 0, 3] = 0.8
    data_color[tile_counts == 0, 3] = 0.0
    return data_color
