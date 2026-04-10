import argparse
import datetime
import logging
import pathlib
import pprint
import shutil
import uuid
import zoneinfo

import exifread
import sqlalchemy
from PIL import Image, ImageOps
from timezonefinder import TimezoneFinder

_tz_finder = TimezoneFinder()

from .config import ConfigAccessor
from .datamodel import DB, Activity, Photo
from .paths import PHOTOS_DIR

logger = logging.getLogger(__name__)

PHOTO_UPLOAD_DIR = pathlib.Path("photo-upload")
THUMBNAIL_SIZES = (128, 512)


def ratio_to_decimal(numbers: list[exifread.utils.Ratio]) -> float:
    deg, min, sec = numbers.values
    return deg.decimal() + min.decimal() / 60 + sec.decimal() / 3600


def get_metadata_from_image(path: pathlib.Path) -> dict:
    with open(path, "rb") as f:
        tags = exifread.process_file(f)
    metadata = {}
    try:
        lat = ratio_to_decimal(tags["GPS GPSLatitude"])
        lon = ratio_to_decimal(tags["GPS GPSLongitude"])
        if str(tags.get("GPS GPSLatitudeRef", "N")) == "S":
            lat = -lat
        if str(tags.get("GPS GPSLongitudeRef", "E")) == "W":
            lon = -lon
        metadata["latitude"] = lat
        metadata["longitude"] = lon
    except KeyError:
        pass
    try:
        dt_str = str(tags["EXIF DateTimeOriginal"])
        if "EXIF OffsetTime" in tags:
            offset = str(tags["EXIF OffsetTime"]).replace(":", "")
            metadata["time"] = datetime.datetime.strptime(
                dt_str + offset, "%Y:%m:%d %H:%M:%S%z"
            ).astimezone(zoneinfo.ZoneInfo("UTC"))
        else:
            # No timezone in EXIF — infer from GPS if available, else assume UTC
            naive_dt = datetime.datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            if "latitude" in metadata and "longitude" in metadata:
                tz_name = _tz_finder.timezone_at(
                    lat=metadata["latitude"], lng=metadata["longitude"]
                )
                if tz_name:
                    local_tz = zoneinfo.ZoneInfo(tz_name)
                    metadata["time"] = naive_dt.replace(tzinfo=local_tz).astimezone(
                        zoneinfo.ZoneInfo("UTC")
                    )
                else:
                    metadata["time"] = naive_dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
            else:
                metadata["time"] = naive_dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
    except KeyError:
        pass

    return metadata


def process_photo(source_path: pathlib.Path, config_accessor: ConfigAccessor | None = None) -> tuple[Photo | None, str | None]:
    """Process a single image file: extract metadata, match activity, generate thumbnails.

    Returns (Photo, None) on success or (None, error_message) on failure.
    The source file is deleted on success.
    """
    metadata = get_metadata_from_image(source_path)

    time: datetime.datetime | None = metadata.get("time")
    grace = datetime.timedelta(minutes=config_accessor().photo_grace_period_minutes if config_accessor else 10)

    activity = None
    no_activity = True

    if time is not None:
        activity = DB.session.scalar(
            sqlalchemy.select(Activity)
            .where(
                Activity.start.is_not(None),
                Activity.elapsed_time.is_not(None),
                Activity.start <= time + grace,
            )
            .order_by(Activity.start.desc())
            .limit(1)
        )
        no_activity = (
            activity is None
            or activity.start_utc is None
            or activity.elapsed_time is None
            or activity.start_utc - grace > time
            or activity.start_utc + activity.elapsed_time + grace < time
        )

    if no_activity:
        standalone_enabled = config_accessor and config_accessor().photo_import_standalone
        if not standalone_enabled:
            if time is None:
                return None, f"'{source_path.name}' has no EXIF DateTimeOriginal and cannot be dated."
            else:
                return None, f"'{source_path.name}' is from {time} but no matching activity was found."
        if "latitude" not in metadata:
            return None, f"'{source_path.name}' has no GPS coordinates and no matching activity — cannot import as standalone."
        activity = None

    if time is not None:
        existing = DB.session.scalar(sqlalchemy.select(Photo).where(Photo.time == time))
        if existing:
            source_path.unlink(missing_ok=True)
            return None, f"'{source_path.name}' already imported (duplicate timestamp {time}), deleted from upload folder."

    if not no_activity and "latitude" not in metadata:
        time_series = activity.time_series
        row = time_series.loc[time_series["time"] >= time].iloc[0]
        metadata["latitude"] = row["latitude"]
        metadata["longitude"] = row["longitude"]

    filename = str(uuid.uuid4()) + source_path.suffix
    webp_filename = pathlib.Path(filename).with_suffix(".webp")

    original_path = PHOTOS_DIR() / "original" / filename
    original_path.parent.mkdir(exist_ok=True)

    shutil.copy2(source_path, original_path)

    with Image.open(original_path) as im:
        im = ImageOps.exif_transpose(im)
        for size in THUMBNAIL_SIZES:
            thumb_path = PHOTOS_DIR() / f"size-{size}" / webp_filename
            thumb_path.parent.mkdir(exist_ok=True)
            thumb = ImageOps.contain(im, (size, size))
            thumb.save(thumb_path)
    original_path.unlink()

    photo = Photo(
        filename=filename,
        time=time,
        latitude=metadata["latitude"],
        longitude=metadata["longitude"],
        activity=activity,
    )
    DB.session.add(photo)
    DB.session.commit()

    source_path.unlink()
    return photo, None


def import_photos_from_folder(basedir: pathlib.Path, config_accessor: ConfigAccessor | None = None):
    upload_dir = basedir / PHOTO_UPLOAD_DIR
    if not upload_dir.exists():
        msg = f"Upload folder does not exist: {upload_dir}"
        logger.error(msg)
        yield msg
        return

    image_extensions = {".jpg", ".jpeg", ".png"}
    files = [f for f in sorted(upload_dir.iterdir()) if f.suffix.lower() in image_extensions]

    if not files:
        msg = "No image files found in photo-upload folder."
        logger.info(msg)
        yield msg
        return

    msg = f"Found {len(files)} image(s) to import."
    logger.info(msg)
    yield msg

    success = 0
    for path in files:
        try:
            photo, error = process_photo(path, config_accessor)
        except Exception as e:
            msg = f"ERROR {path.name}: {e}"
            logger.exception(msg)
            yield msg
            continue
        if error:
            msg = f"SKIP  {path.name}: {error}"
            logger.warning(msg)
        else:
            if photo.activity_id:
                activity_info = f"activity {photo.activity_id} - '{photo.activity.name}'"
            else:
                activity_info = "standalone"
            msg = f"OK    {path.name} → {activity_info}"
            logger.info(msg)
            success += 1
        yield msg

    msg = f"Done. {success}/{len(files)} imported successfully."
    logger.info(msg)
    yield msg


def main_inspect_photo(options: argparse.Namespace) -> None:
    path: pathlib.Path = options.path
    metadata = get_metadata_from_image(path)
    pprint.pprint(metadata)
