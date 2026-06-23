"""Application constants, paths, and configuration."""

import logging
import platform
import tomllib
from pathlib import Path

from platformdirs import PlatformDirs

_log = logging.getLogger(__name__)

# --- Application identity ---
APP_NAME = "flufy"
DESKTOP_FILE_NAME = "flufy.desktop"

# --- Platform directories (XDG-compliant) ---
# Don't create dirs at import time; callers mkdir() when actually writing.
_dirs = PlatformDirs(APP_NAME)
_XDG_DATA_HOME = Path(_dirs.user_data_dir).parent  # e.g. ~/.local/share
DESKTOP_FILE = _XDG_DATA_HOME / "applications" / DESKTOP_FILE_NAME

CONFIG_DIR = Path(_dirs.user_config_dir)
DATA_DIR = Path(_dirs.user_data_dir)
CACHE_DIR = Path(_dirs.user_cache_dir)
LOG_DIR = Path(_dirs.user_log_dir)

# --- Filesystem paths ---
WEBENGINE_DIR = DATA_DIR / "webengine"
SOCK_PATH = DATA_DIR / "app.sock"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# --- Default values ---
_DEFAULTS: dict[str, str | int] = {
    "target_url": "https://app.slack.com/client",
    "window_title": "Flufy",
    "window_width": 1200,
    "window_height": 800,
    "chrome_full_version": "140.0.7339.225",
    "unread_poll_ms": 3000,
}


def _load_config() -> dict[str, str | int]:
    """Load user config from TOML, falling back to defaults."""
    cfg: dict[str, str | int] = dict(_DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE, "rb") as f:
                user_cfg = tomllib.load(f)
            for key, value in user_cfg.items():
                if key not in _DEFAULTS:
                    _log.warning("unknown configuration key: %s", key)
                    continue
                expected_type = type(_DEFAULTS[key])
                if type(value) is expected_type:
                    cfg[key] = value
                else:
                    _log.warning(
                        "invalid type for %s: %r (expected %s), using default",
                        key,
                        value,
                        expected_type.__name__,
                    )
        except (tomllib.TOMLDecodeError, OSError):
            _log.warning(
                "failed to load %s, using defaults", CONFIG_FILE, exc_info=True
            )
    return cfg


_cfg = _load_config()

# --- Target URLs ---
TARGET_URL: str = str(_cfg["target_url"])

# --- Window defaults ---
WINDOW_TITLE: str = str(_cfg["window_title"])
WINDOW_WIDTH: int = int(_cfg["window_width"])
WINDOW_HEIGHT: int = int(_cfg["window_height"])

# --- Chrome UA spoofing ---
CHROME_FULL_VERSION: str = str(_cfg["chrome_full_version"])
CHROME_VERSION: str = CHROME_FULL_VERSION.split(".")[0]
_MACHINE = platform.machine() or "x86_64"
_OS_STR = {
    "Darwin": "Macintosh; Intel Mac OS X 10_15_7",
    "Windows": "Windows NT 10.0; Win64; x64",
}.get(platform.system(), f"X11; Linux {_MACHINE}")
CHROME_UA = (
    f"Mozilla/5.0 ({_OS_STR}) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) Chrome/{CHROME_FULL_VERSION} Safari/537.36"
)

# --- Platform hints (for JS navigator overrides) ---
PLATFORM_STRING = f"Linux {_MACHINE}"
ARCH: str = {"x86_64": "x86", "AMD64": "x86", "aarch64": "arm", "arm64": "arm"}.get(
    _MACHINE, "x86"
)
BITNESS = "64"

# --- Timing ---
UNREAD_POLL_MS: int = int(_cfg["unread_poll_ms"])
