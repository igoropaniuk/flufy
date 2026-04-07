"""Deep-link handling, single-instance IPC, and desktop registration."""

import logging
import re
import socket
import subprocess
import sys
import threading
import urllib.parse
from collections.abc import Callable
from pathlib import Path

from flufy.config import APP_NAME, DATA_DIR, DESKTOP_FILE, SOCK_PATH, TARGET_URL

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deep-link parsing
# ---------------------------------------------------------------------------


def parse_deep_link(slack_uri: str) -> tuple[str | None, str | None]:
    """Extract ``(team_id, magic_token)`` from a ``slack://`` URI.

    Format: ``slack://TEAM_ID/magic-login/TOKEN?id=N``
    """
    path = slack_uri.removeprefix("slack://").split("?")[0]
    match = re.match(r"^([^/]+)/magic-login/(.+)$", path)
    if match:
        return match.group(1), match.group(2)
    return None, None


def deep_link_to_url(slack_uri: str) -> str:
    """Convert a ``slack://`` magic-login deep link to an HTTPS URL."""
    team_id, magic_token = parse_deep_link(slack_uri)
    if team_id and magic_token:
        params = urllib.parse.urlencode(
            {"magic_token": magic_token, "team_id": team_id}
        )
        return f"https://slack.com/ssb/redirect?{params}"
    return TARGET_URL


# ---------------------------------------------------------------------------
# Single-instance IPC via Unix domain socket
# ---------------------------------------------------------------------------


def send_to_running_instance(message: str) -> bool:
    """Send a message to an already-running instance. Return *True* on success."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(SOCK_PATH))
            sock.sendall(message.encode())
        log.info("sent message to running instance via IPC: %s", message)
        return True
    except (ConnectionRefusedError, FileNotFoundError):
        log.debug("no running instance found at %s", SOCK_PATH)
        return False


def _recv_message(conn: socket.socket) -> str | None:
    """Read a complete message from *conn*, returning None on failure."""
    conn.settimeout(5.0)
    chunks: list[bytes] = []
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    except (TimeoutError, OSError):
        log.warning("IPC connection timed out or errored, ignoring")
        return None
    try:
        data = b"".join(chunks).decode().strip()
    except UnicodeDecodeError:
        log.warning("IPC received invalid data, ignoring")
        return None
    return data or None


def start_ipc_listener(
    on_url: Callable[[str], object],
    on_show: Callable[[], object],
) -> None:
    """Spawn a daemon thread that accepts IPC messages on a Unix socket.

    Recognised messages:
    - ``show`` -- bring the window to the foreground
    - anything starting with ``slack://`` -- navigate to the deep-link URL
    """

    def _listen() -> None:
        """Accept connections in a loop and dispatch messages."""
        SOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        SOCK_PATH.unlink(missing_ok=True)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            try:
                server.bind(str(SOCK_PATH))
            except OSError:
                log.exception("failed to bind IPC socket at %s", SOCK_PATH)
                return
            server.listen(1)
            log.info("IPC listener started on %s", SOCK_PATH)
            while True:
                conn, _ = server.accept()
                with conn:
                    data = _recv_message(conn)
                if data is None:
                    continue
                log.info("IPC received: %s", data)
                if data == "show":
                    on_show()
                else:
                    on_url(deep_link_to_url(data))

    thread = threading.Thread(target=_listen, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# Desktop protocol-handler registration
# ---------------------------------------------------------------------------


def install_desktop_handler() -> Path:
    """Register as the ``slack://`` protocol handler and return the .desktop path."""
    png_path = DATA_DIR / "icon.png"

    desktop_entry = (
        "[Desktop Entry]\n"
        f"Name={APP_NAME}\n"
        f'Exec="{sys.executable}" -m flufy %u\n'
        "Type=Application\n"
        f"Icon={png_path}\n"
        f"StartupWMClass={APP_NAME}\n"
        "MimeType=x-scheme-handler/slack;\n"
        "NoDisplay=false\n"
    )

    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_FILE.write_text(desktop_entry)
    log.info("wrote desktop file %s", DESKTOP_FILE)

    subprocess.run(
        ["xdg-mime", "default", DESKTOP_FILE.name, "x-scheme-handler/slack"],
        check=False,
    )
    subprocess.run(
        ["update-desktop-database", str(DESKTOP_FILE.parent)],
        capture_output=True,
        check=False,
    )

    return DESKTOP_FILE
