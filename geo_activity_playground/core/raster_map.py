import dataclasses
import logging

import numpy as np

from .tiles import compute_tile_float

logger = logging.getLogger(__name__)


OSM_TILE_SIZE = 256  # OSM tile size in pixel
OSM_MAX_ZOOM = 19  # OSM maximum zoom level
MAX_TILE_COUNT = 2000  # maximum number of tiles to download

## Basic data types ##


@dataclasses.dataclass
class GeoBounds:
    """
    Models an area on the globe as a rectangle of latitude and longitude.

    Latitude goes from South Pole (-90°) to North Pole (+90°). Longitude goes from West (-180°) to East (+180°). Be careful when converting latitude to Y-coordinates as increasing latitude will mean decreasing Y.
    """

    lat_min: float
    lon_min: float
    lat_max: float
    lon_max: float


@dataclasses.dataclass
class TileBounds:
    zoom: int
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclasses.dataclass
class PixelBounds:
    x1: int
    y1: int
    x2: int
    y2: int

    @classmethod
    def from_tile_bounds(cls, tile_bounds: TileBounds) -> "PixelBounds":
        return pixel_bounds_from_tile_bounds(tile_bounds)

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def shape(self) -> tuple[int, int]:
        return self.height, self.width


@dataclasses.dataclass
class RasterMapImage:
    image: np.ndarray
    tile_bounds: TileBounds
    geo_bounds: GeoBounds
    pixel_bounds: PixelBounds


## Converter functions ##


def pixel_bounds_from_tile_bounds(tile_bounds: TileBounds) -> PixelBounds:
    return PixelBounds(
        int(tile_bounds.x1 * OSM_TILE_SIZE),
        int(tile_bounds.y1 * OSM_TILE_SIZE),
        int(tile_bounds.x2 * OSM_TILE_SIZE),
        int(tile_bounds.y2 * OSM_TILE_SIZE),
    )


def get_sensible_zoom_level(
    bounds: GeoBounds, picture_size: tuple[int, int]
) -> TileBounds:
    zoom = OSM_MAX_ZOOM

    while True:
        x_tile_min, y_tile_max = map(
            int, compute_tile_float(bounds.lat_min, bounds.lon_min, zoom)
        )
        x_tile_max, y_tile_min = map(
            int, compute_tile_float(bounds.lat_max, bounds.lon_max, zoom)
        )

        x_tile_max += 1
        y_tile_max += 1

        if (x_tile_max - x_tile_min) * OSM_TILE_SIZE <= picture_size[0] and (
            y_tile_max - y_tile_min
        ) * OSM_TILE_SIZE <= picture_size[1]:
            break

        zoom -= 1

    tile_count = (x_tile_max - x_tile_min) * (y_tile_max - y_tile_min)

    if tile_count > MAX_TILE_COUNT:
        raise RuntimeError("Zoom value too high, too many tiles to download")

    return TileBounds(zoom, x_tile_min, y_tile_min, x_tile_max, y_tile_max)
