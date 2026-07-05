"""QtWebEngine browser widget with Chrome UA spoofing."""

from pathlib import Path

from PyQt6.QtCore import QByteArray, QObject, QStandardPaths, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEnginePermission,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QFileDialog

from flufy.config import (
    APP_NAME,
    ARCH,
    ASSETS_DIR,
    BITNESS,
    CACHE_DIR,
    CHROME_FULL_VERSION,
    CHROME_UA,
    CHROME_VERSION,
    PLATFORM_STRING,
    WEBENGINE_DIR,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from flufy.icons import load_svg_icon
from flufy.notify import show_notification

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _ChromeUAInterceptor(QWebEngineUrlRequestInterceptor):
    """Rewrite ``Sec-CH-UA`` headers to present a real Chrome identity."""

    def interceptRequest(self, info) -> None:  # noqa: N802
        """Inject spoofed Sec-CH-UA headers into every outgoing request."""
        info.setHttpHeader(
            QByteArray(b"Sec-CH-UA"),
            QByteArray(
                f'"Chromium";v="{CHROME_VERSION}", '
                f'"Google Chrome";v="{CHROME_VERSION}", '
                f'"Not)A;Brand";v="8"'.encode()
            ),
        )
        info.setHttpHeader(
            QByteArray(b"Sec-CH-UA-Full-Version-List"),
            QByteArray(
                f'"Chromium";v="{CHROME_FULL_VERSION}", '
                f'"Google Chrome";v="{CHROME_FULL_VERSION}", '
                f'"Not)A;Brand";v="8.0.0.0"'.encode()
            ),
        )
        info.setHttpHeader(
            QByteArray(b"Sec-CH-UA-Platform"),
            QByteArray(b'"Linux"'),
        )


class _ExternalLinkPage(QWebEnginePage):
    """Throwaway page that hands its first navigation off to the system browser."""

    def __init__(
        self,
        profile: QWebEngineProfile | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create the page, ensuring it is freed if the popup closes itself."""
        if profile is not None:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        # Cover popups that load about:blank but never navigate to a real URL.
        self.windowCloseRequested.connect(self.deleteLater)

    def acceptNavigationRequest(  # noqa: N802
        self,
        url: QUrl,
        _type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        """Open *url* externally and discard this page."""
        # Let the engine handle schemes the system browser can't (or shouldn't):
        # the about:blank that some window.open() flows emit before the real
        # navigation, javascript: code, and origin-bound blob: URLs.
        if not is_main_frame or url.scheme() in ("about", "javascript", "blob"):
            return True
        QDesktopServices.openUrl(url)
        self.deleteLater()
        return False


class _AppPage(QWebEnginePage):
    """Custom page that auto-grants notification and clipboard permissions."""

    # Permission types we silently grant. ClipboardReadWrite is what lets the web
    # client's own copy/paste round-trip through navigator.clipboard.read(): on
    # Qt 6.8+ that async read is gated behind this permission, separately from the
    # JavascriptCanPaste setting (which only covers the native paste event).
    _AUTO_GRANT = frozenset(
        {
            QWebEnginePermission.PermissionType.Notifications,
            QWebEnginePermission.PermissionType.ClipboardReadWrite,
        }
    )

    def __init__(
        self,
        profile: QWebEngineProfile | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create the page, wiring up the permission handler."""
        if profile is not None:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        # Qt 6.8+ (our minimum) delivers notification and clipboard permission
        # requests through permissionRequested, superseding the deprecated
        # featurePermissionRequested signal.
        self.permissionRequested.connect(self._on_permission_requested)

    def _on_permission_requested(self, permission: QWebEnginePermission) -> None:
        """Auto-grant the notification and clipboard permission requests."""
        if permission.permissionType() in self._AUTO_GRANT:
            permission.grant()

    def createWindow(  # noqa: N802
        self, _type: QWebEnginePage.WebWindowType
    ) -> QWebEnginePage:
        """Route ``window.open`` / ``target=_blank`` clicks to the system browser."""
        return _ExternalLinkPage(self.profile(), self)


def _load_override_js() -> str:
    """Read ``overrides.js`` and fill in all template placeholders."""
    template = (ASSETS_DIR / "overrides.js").read_text()
    return (
        template.replace("{{CHROME_UA}}", CHROME_UA)
        .replace("{{CHROME_VERSION}}", CHROME_VERSION)
        .replace("{{CHROME_FULL_VERSION}}", CHROME_FULL_VERSION)
        .replace("{{PLATFORM_STRING}}", PLATFORM_STRING)
        .replace("{{ARCH}}", ARCH)
        .replace("{{BITNESS}}", BITNESS)
    )


# ---------------------------------------------------------------------------
# Public widget
# ---------------------------------------------------------------------------


class Browser(QWebEngineView):
    """Main browser window wrapping the web client."""

    # Thread-safe signals used by the IPC listener.
    url_requested = pyqtSignal(str)
    show_requested = pyqtSignal()

    def __init__(self) -> None:
        """Set up the window, WebEngine profile, and JS overrides."""
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(load_svg_icon(str(ASSETS_DIR / "icon.svg")))
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        profile = self._create_profile()
        page = _AppPage(profile, self)
        self._inject_overrides(page)
        self._enable_clipboard(page)
        self.setPage(page)

        self._was_maximized = False
        self.url_requested.connect(self._on_url_requested)
        self.show_requested.connect(self._on_show_requested)

    # -- setup helpers -------------------------------------------------------

    def _create_profile(self) -> QWebEngineProfile:
        """Build a persistent WebEngine profile with Chrome UA and cookie settings."""
        WEBENGINE_DIR.mkdir(parents=True, exist_ok=True)

        profile = QWebEngineProfile(APP_NAME, self)
        profile.setPersistentStoragePath(str(WEBENGINE_DIR))
        profile.setCachePath(str(CACHE_DIR))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        profile.setHttpUserAgent(CHROME_UA)

        # Must be kept alive as a reference; Qt won't prevent GC.
        self._interceptor = _ChromeUAInterceptor(self)
        profile.setUrlRequestInterceptor(self._interceptor)

        profile.setNotificationPresenter(show_notification)
        profile.downloadRequested.connect(self._on_download_requested)
        return profile

    def _on_download_requested(self, download: QWebEngineDownloadRequest) -> None:
        """Prompt the user to confirm the save location before accepting."""
        # writableLocation() can return "" on headless/misconfigured systems;
        # Path("").mkdir() would raise, so fall back to ~/Downloads.
        download_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        downloads = Path(download_dir) if download_dir else Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)

        # suggestedFileName() is server-controlled; strip it to a bare basename so
        # it can't steer the default path elsewhere via "../" or an absolute path.
        suggested_name = Path(download.suggestedFileName()).name or "download"
        suggested = downloads / suggested_name
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", str(suggested))
        if not file_path:
            download.cancel()
            return

        save_path = Path(file_path)
        download.setDownloadDirectory(str(save_path.parent))
        download.setDownloadFileName(save_path.name)
        download.accept()

    @staticmethod
    def _inject_overrides(page: _AppPage) -> None:
        """Register the Chrome-spoofing script to run at document creation."""
        script = QWebEngineScript()
        script.setName("flufy-overrides")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        script.setSourceCode(_load_override_js())
        page.scripts().insert(script)

    @staticmethod
    def _enable_clipboard(page: _AppPage) -> None:
        """Allow the page's JS to read/write the system clipboard (e.g. copy image)."""
        settings = page.settings()
        if settings is None:
            return
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)

    # -- navigation ----------------------------------------------------------

    def navigate(self, url: str) -> None:
        """Load *url* in the browser."""
        self.setUrl(QUrl(url))

    def _on_url_requested(self, url: str) -> None:
        """Slot called by the IPC listener signal to navigate to *url*."""
        self.navigate(url)
        self.restore_window()

    def _on_show_requested(self) -> None:
        """Bring the window to the foreground."""
        self.restore_window()

    def restore_window(self) -> None:
        """Show the window, preserving maximized state."""
        if self.isVisible():
            self.raise_()
        elif self._was_maximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.activateWindow()

    # -- close-to-tray -------------------------------------------------------

    def hide_to_tray(self) -> None:
        """Save window state and hide to tray."""
        self._was_maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)
        self.hide()

    def closeEvent(self, event) -> None:  # noqa: N802
        """Hide the window instead of destroying it (minimize-to-tray)."""
        event.ignore()
        self.hide_to_tray()
