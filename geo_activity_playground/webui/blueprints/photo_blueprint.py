import pathlib
import tempfile

import geojson
import sqlalchemy
from flask import Blueprint, Response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ...core.config import ConfigAccessor
from ...core.datamodel import DB, Activity, Photo
from ...core.paths import PHOTOS_DIR
from ...core.photos import PHOTO_UPLOAD_DIR, import_photos_from_folder, process_photo
from ..authenticator import Authenticator
from ..flasher import Flasher, FlashTypes


def make_photo_blueprint(
    config_accessor: ConfigAccessor, authenticator: Authenticator, flasher: Flasher
) -> Blueprint:
    blueprint = Blueprint("photo", __name__, template_folder="templates")

    @blueprint.route("/get/<int:id>/<int:size>.webp")
    def get(id: int, size: int) -> Response:
        assert size in (128, 512)
        photo = DB.session.get_one(Photo, id)

        small_path = PHOTOS_DIR() / f"size-{size}" / photo.path.with_suffix(".webp")

        with open(small_path, "rb") as f:
            return Response(f.read(), mimetype="image/webp")

    @blueprint.route("/map")
    def map() -> str:
        return render_template("photo/map.html.j2")

    @blueprint.route("/map-for-all/photos.geojson")
    def map_for_all() -> Response:
        photos = DB.session.scalars(sqlalchemy.select(Photo)).all()
        fc = geojson.FeatureCollection(
            features=[
                geojson.Feature(
                    geometry=geojson.Point((photo.longitude, photo.latitude)),
                    properties={
                        "photo_id": photo.id,
                        "activity_id": photo.activity_id,
                        "url_marker": url_for(".get", id=photo.id, size=128),
                        "url_popup": url_for(".get", id=photo.id, size=512),
                        "url_full": url_for(".get", id=photo.id, size=512),
                        "url_activity": url_for(
                            "activity.show", id=photo.activity_id
                        )
                        if photo.activity_id
                        else None,
                    },
                )
                for photo in photos
            ]
        )
        return Response(
            geojson.dumps(fc, sort_keys=True, indent=2, ensure_ascii=False),
            mimetype="application/json",
        )

    @blueprint.route("/map-for-activity/<int:activity_id>/photos.geojson")
    def map_for_activity(activity_id: int) -> Response:
        activity = DB.session.get_one(Activity, activity_id)
        fc = geojson.FeatureCollection(
            features=[
                geojson.Feature(
                    geometry=geojson.Point((photo.longitude, photo.latitude)),
                    properties={
                        "photo_id": photo.id,
                        "activity_id": activity_id,
                        "url_marker": url_for(".get", id=photo.id, size=128),
                        "url_popup": url_for(".get", id=photo.id, size=512),
                        "url_full": url_for(".get", id=photo.id, size=512),
                        "url_activity": url_for("activity.show", id=activity_id),
                    },
                )
                for photo in activity.photos
            ]
        )
        return Response(
            geojson.dumps(fc, sort_keys=True, indent=2, ensure_ascii=False),
            mimetype="application/json",
        )

    @blueprint.route("/bulk-import")
    def bulk_import() -> Response:
        from flask import current_app
        app = current_app._get_current_object()
        basedir = pathlib.Path.cwd()

        def generate():
            with app.app_context():
                for line in import_photos_from_folder(basedir, config_accessor):
                    yield f"data: {line}\n\n"
                yield "data: __done__\n\n"

        return Response(generate(), mimetype="text/event-stream")

    @blueprint.route("/new", methods=["GET", "POST"])
    def new() -> ResponseReturnValue:
        if request.method == "POST":
            # check if the post request has the file part
            if "file" not in request.files:
                flasher.flash_message(
                    "No file could be found. Did you select a file?", FlashTypes.WARNING
                )
                return redirect(url_for(".new"))

            new_photos: list[Photo] = []
            for file in request.files.getlist("file"):
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                if file.filename == "":
                    flasher.flash_message("No selected file.", FlashTypes.WARNING)
                    return redirect(url_for(".new"))
                if not file:
                    flasher.flash_message("Empty file uploaded.", FlashTypes.WARNING)
                    return redirect(url_for(".new"))

                suffix = pathlib.Path(file.filename).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp_path = pathlib.Path(tmp.name)
                file.save(tmp_path)

                photo, error = process_photo(tmp_path, config_accessor)
                if error:
                    tmp_path.unlink(missing_ok=True)
                    flasher.flash_message(error, FlashTypes.DANGER)
                    continue
                new_photos.append(photo)

            if new_photos:
                flasher.flash_message(
                    f"Added {len(new_photos)} new photos.", FlashTypes.SUCCESS
                )
                return redirect(f"/activity/{new_photos[-1].activity.id}")
            else:
                return redirect(url_for(".new"))
        else:
            return render_template("photo/new.html.j2")

    return blueprint
