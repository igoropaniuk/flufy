"""Application orchestration - creates and wires all components."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from flufy.browser import Browser
from flufy.config import APP_NAME, ASSETS_DIR, DATA_DIR, DESKTOP_FILE, TARGET_URL
from flufy.icons import create_png_icon
from flufy.protocol import install_desktop_handler, start_ipc_listener
from flufy.tray import create_tray

log = logging.getLogger(__name__)


def _ensure_desktop_setup() -> None:
    """Create PNG icon and register the .desktop file if missing."""
    png_path = DATA_DIR / "icon.png"
    if not png_path.exists():
        create_png_icon(str(ASSETS_DIR / "icon.svg"), str(png_path))
        log.info("created PNG icon at %s", png_path)

    if not DESKTOP_FILE.exists():
        try:
            install_desktop_handler()
        except Exception:
            log.warning("failed to install desktop handler", exc_info=True)


def run(initial_url: str | None = None) -> None:
    """Start the Qt application with all components wired together."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    _ensure_desktop_setup()

    browser = Browser()
    app.setWindowIcon(browser.windowIcon())

    # Tray icon + unread polling.
    # Local variables are sufficient to prevent GC as run() blocks on app.exec().
    _tray, _monitor = create_tray(browser)

    # IPC listener: deep links navigate, "show" brings window to front.
    start_ipc_listener(browser.url_requested.emit, browser.show_requested.emit)

    url = initial_url or TARGET_URL
    log.info("navigating to %s", url)
    browser.navigate(url)
    browser.show()

    sys.exit(app.exec())
