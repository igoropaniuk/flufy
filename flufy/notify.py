"""Desktop notification forwarding via notify-send."""

import logging
import subprocess

from PyQt6.QtWebEngineCore import QWebEngineNotification

from flufy.config import DATA_DIR

log = logging.getLogger(__name__)


def show_notification(notification: QWebEngineNotification) -> None:
    """Forward a QtWebEngine notification to the Linux desktop."""
    title = notification.title() or "Flufy"
    message = notification.message() or ""

    icon_args: list[str] = []
    icon = notification.icon()
    if not icon.isNull():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        icon_path = str(DATA_DIR / "notification-icon.png")
        icon.save(icon_path)
        icon_args = ["-i", icon_path]

    try:
        subprocess.Popen(
            ["notify-send", *icon_args, "--app-name=Flufy", title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        log.warning("notify-send not found; desktop notifications disabled")

    notification.show()
