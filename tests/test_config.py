"""Tests for flufy.config - sanity checks on constants and paths."""

from flufy.config import ASSETS_DIR, CHROME_FULL_VERSION, CHROME_UA, CHROME_VERSION


def test_chrome_version_consistency() -> None:
    """Full version string should start with the short version."""
    assert CHROME_FULL_VERSION.startswith(CHROME_VERSION)
    assert CHROME_VERSION in CHROME_UA
    assert CHROME_FULL_VERSION in CHROME_UA


def test_assets_dir_exists() -> None:
    """Assets directory is present in the installed package."""
    assert ASSETS_DIR.is_dir()


def test_required_assets_present() -> None:
    """All expected static asset files exist in the assets directory."""
    assert (ASSETS_DIR / "icon.svg").is_file()
    assert (ASSETS_DIR / "icon_unread.svg").is_file()
    assert (ASSETS_DIR / "overrides.js").is_file()


def test_overrides_js_has_placeholders() -> None:
    """The template file should contain markers that Python replaces."""
    js = (ASSETS_DIR / "overrides.js").read_text()
    assert "{{CHROME_UA}}" in js
    assert "{{CHROME_VERSION}}" in js
    assert "{{CHROME_FULL_VERSION}}" in js
    assert "{{PLATFORM_STRING}}" in js
    assert "{{ARCH}}" in js
    assert "{{BITNESS}}" in js
