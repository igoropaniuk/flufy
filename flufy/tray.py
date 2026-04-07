"""System tray icon with unread-message monitoring."""

import subprocess

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from flufy.browser import Browser
from flufy.config import ASSETS_DIR, UNREAD_POLL_MS
from flufy.icons import load_svg_icon

# JS snippet executed every poll cycle to detect unread indicators.
_UNREAD_JS = """
(function() {
    var badges = document.querySelectorAll(
        '.p-channel_sidebar__badge, ' +
        '[data-qa="channel_sidebar_badge"], ' +
        '.c-mention_badge, ' +
        '.p-channel_sidebar__channel--unread'
    );
    var favicon = document.querySelector('link[rel*="icon"]');
    var faviconHint = favicon && favicon.href &&
                      favicon.href.indexOf('favicon-urgent') !== -1;
    return badges.length > 0 || !!faviconHint;
})();
"""


def _load_icon(unread: bool = False) -> QIcon:
    """Return the normal or unread-state tray icon."""
    name = "icon_unread.svg" if unread else "icon.svg"
    return load_svg_icon(str(ASSETS_DIR / name))


def _play_sound() -> None:
    """Play the system notification sound (best-effort)."""
    try:
        subprocess.Popen(
            ["canberra-gtk-play", "-i", "message-new-instant"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


class UnreadMonitor:
    """Polls the browser DOM for unread indicators and updates the tray."""

    def __init__(self, browser: Browser, tray: QSystemTrayIcon) -> None:
        """Start the polling timer and preload both icon states."""
        self._browser = browser
        self._tray = tray
        self._has_unread = False
        self._icon_normal = _load_icon(unread=False)
        self._icon_unread = _load_icon(unread=True)

        self._timer = QTimer()
        self._timer.timeout.connect(self._poll)
        self._timer.start(UNREAD_POLL_MS)

    def _poll(self) -> None:
        """Run the unread-detection JS snippet in the active page."""
        page = self._browser.page()
        if page is not None:
            page.runJavaScript(_UNREAD_JS, self._on_result)

    def _on_result(self, value: object) -> None:
        """Update tray icon and play sound when unread state changes."""
        unread = bool(value)
        if unread == self._has_unread:
            return
        self._has_unread = unread
        self._tray.setIcon(self._icon_unread if unread else self._icon_normal)
        self._tray.setToolTip(
            "Flufy - new messages" if unread else "Flufy - no new messages"
        )
        if unread:
            _play_sound()


def create_tray(browser: Browser) -> tuple[QSystemTrayIcon, UnreadMonitor]:
    """Build the system-tray icon, context menu, and unread monitor."""
    icon = _load_icon()
    tray = QSystemTrayIcon(icon)
    tray.setToolTip("Flufy")

    # --- context menu ---
    menu = QMenu()
    show_action = menu.addAction("Show Flufy")
    assert show_action is not None
    show_action.triggered.connect(browser.restore_window)

    quit_action = menu.addAction("Quit")
    assert quit_action is not None
    app = QApplication.instance()
    assert app is not None
    quit_action.triggered.connect(app.quit)

    tray.setContextMenu(menu)

    # --- toggle on click ---
    def _on_activated(reason: QSystemTrayIcon.ActivationReason) -> None:
        """Toggle browser visibility on single-click of the tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if browser.isVisible():
                browser.hide_to_tray()
            else:
                browser.restore_window()

    tray.activated.connect(_on_activated)
    tray.show()

    monitor = UnreadMonitor(browser, tray)
    return tray, monitor
