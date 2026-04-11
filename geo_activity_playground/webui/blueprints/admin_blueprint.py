import atexit
import logging
import os
import threading
import time

from flask import Blueprint
from flask.typing import ResponseReturnValue

from ..authenticator import Authenticator

logger = logging.getLogger(__name__)


def make_admin_blueprint(authenticator: Authenticator) -> Blueprint:
    blueprint = Blueprint("admin", __name__, template_folder="templates")

    @blueprint.route("/shutdown", methods=["POST"])
    def shutdown() -> ResponseReturnValue:
        logger.info("Shutdown requested via web interface.")

        # Run in a background thread with a short delay so the 204 response is
        # delivered before the process exits. We call atexit._run_exitfuncs()
        # explicitly to trigger registered cleanup handlers (e.g. DB dispose)
        # before os._exit(), which bypasses Waitress's drain-and-wait logic
        # (channel_timeout=180 would cause a 3-minute hang via SIGTERM).
        def _deferred_shutdown() -> None:
            time.sleep(0.5)
            logger.info("Running atexit handlers before shutdown.")
            atexit._run_exitfuncs()
            logger.info("Exiting process.")
            os._exit(0)

        threading.Thread(target=_deferred_shutdown, daemon=True).start()
        return "", 204

    return blueprint

