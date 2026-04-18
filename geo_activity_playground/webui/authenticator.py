from flask import flash, redirect, session, url_for

from ..core.config import Config

PUBLIC_ENDPOINTS = frozenset({
    "static",         # Flask built-in static file serving
    "auth.index",     # login page (GET + POST)
    "auth.logout",
    "heatmap.tile",   # heatmap tiles         /heatmap/tile/<z>/<x>/<y>.png
    "explorer.tile",  # explorer tiles        /explorer/<zoom>/tile/<z>/<x>/<y>.png
})


class Authenticator:
    def __init__(self, config: Config) -> None:
        self._config = config

    def is_authenticated(self) -> bool:
        return not self._config.upload_password or session.get(
            "is_authenticated", False
        )

    def authenticate(self, password: str) -> None:
        if password == self._config.upload_password:
            session["is_authenticated"] = True
            session.permanent = True
            flash("Login successful.", category="success")
        else:
            flash("Incorrect password.", category="warning")

    def logout(self) -> None:
        session["is_authenticated"] = False
        flash("Logout successful.", category="success")
