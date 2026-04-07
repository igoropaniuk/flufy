"""Smoke tests - verify the Qt application and main widget initialise cleanly.

These tests require a real or virtual display and a working QtWebEngine.
They are skipped automatically in environments where QtWebEngine cannot
initialise (e.g. minimal CI runners).
"""

import os
import sys

import pytest

# QtWebEngine's Chromium subprocess aborts on minimal CI runners even with
# sandbox disabled.  The import itself triggers Chromium init, so we must
# skip before importing.
if os.environ.get("CI") == "true":
    pytest.skip(
        "QtWebEngine requires a full desktop environment",
        allow_module_level=True,
    )

from PyQt6.QtWidgets import QApplication  # noqa: E402

from flufy.browser import Browser  # noqa: E402
from flufy.config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    """Module-scoped QApplication instance shared across all smoke tests."""
    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


@pytest.fixture(scope="module")
def browser(qt_app: QApplication):
    """Shared Browser instance for smoke tests, ensuring proper cleanup."""
    widget = Browser()
    yield widget
    widget.deleteLater()
    qt_app.processEvents()


def test_browser_instantiates(browser: Browser) -> None:
    """Browser widget can be created without raising an exception."""
    assert browser is not None


def test_browser_window_title(browser: Browser) -> None:
    """Browser window title matches the configured WINDOW_TITLE."""
    assert browser.windowTitle() == WINDOW_TITLE


def test_browser_window_size(browser: Browser) -> None:
    """Browser is resized to the configured dimensions on creation."""
    assert browser.width() == WINDOW_WIDTH
    assert browser.height() == WINDOW_HEIGHT


def test_browser_window_icon_set(browser: Browser) -> None:
    """Browser window icon is not null (SVG loaded successfully)."""
    assert not browser.windowIcon().isNull()
