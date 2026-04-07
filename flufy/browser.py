"""QtWebEngine browser widget with Chrome UA spoofing."""

from PyQt6.QtCore import QByteArray, QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

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


class _AppPage(QWebEnginePage):
    """Custom page that auto-grants notification permissions."""

    def __init__(
        self,
        profile: QWebEngineProfile | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create the page, wiring up the feature-permission handler."""
        if profile is not None:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        self.featurePermissionRequested.connect(self._on_feature_permission)

    def _on_feature_permission(
        self, url: QUrl, feature: QWebEnginePage.Feature
    ) -> None:
        """Auto-grant notification permission requests."""
        if feature == QWebEnginePage.Feature.Notifications:
            self.setFeaturePermission(
                url,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            )


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
        return profile

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
