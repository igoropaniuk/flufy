"""Tests for flufy.protocol - deep-link parsing, URL building, IPC."""

import socket
import threading
from pathlib import Path
from unittest.mock import patch

from flufy.protocol import (
    deep_link_to_url,
    install_desktop_handler,
    parse_deep_link,
    send_to_running_instance,
)

# ---------------------------------------------------------------------------
# parse_deep_link
# ---------------------------------------------------------------------------


class TestParseDeepLink:
    """Unit tests for parse_deep_link()."""

    def test_valid_magic_login(self) -> None:
        """Full URI with query string returns correct team and token."""
        uri = "slack://T12345/magic-login/abc-def-ghi?id=1"
        assert parse_deep_link(uri) == ("T12345", "abc-def-ghi")

    def test_valid_without_query(self) -> None:
        """URI without query string still parses correctly."""
        uri = "slack://T99/magic-login/tokenXYZ"
        assert parse_deep_link(uri) == ("T99", "tokenXYZ")

    def test_no_magic_login(self) -> None:
        """Non-magic-login path returns (None, None)."""
        assert parse_deep_link("slack://T99/other/path") == (None, None)

    def test_empty_uri(self) -> None:
        """Empty slack:// URI returns (None, None)."""
        assert parse_deep_link("slack://") == (None, None)

    def test_non_matching_uri(self) -> None:
        """Non-slack URI returns (None, None)."""
        assert parse_deep_link("https://example.com") == (None, None)


# ---------------------------------------------------------------------------
# deep_link_to_url
# ---------------------------------------------------------------------------


class TestDeepLinkToUrl:
    """Unit tests for deep_link_to_url()."""

    def test_valid_link_returns_https(self) -> None:
        """Valid magic-login URI is converted to HTTPS redirect URL."""
        url = deep_link_to_url("slack://T1/magic-login/tok123")
        assert url.startswith("https://slack.com/ssb/redirect?")
        assert "magic_token=tok123" in url
        assert "team_id=T1" in url

    def test_invalid_link_returns_target_url(self) -> None:
        """Unrecognised URI falls back to the default TARGET_URL."""
        url = deep_link_to_url("slack://garbage")
        assert url == "https://app.slack.com/client"


# ---------------------------------------------------------------------------
# send_to_running_instance
# ---------------------------------------------------------------------------


class TestSendToRunningInstance:
    """Unit tests for send_to_running_instance()."""

    def test_returns_false_when_no_socket(self, tmp_path: Path) -> None:
        """Returns False when no instance is listening on the socket path."""
        with patch("flufy.protocol.SOCK_PATH", tmp_path / "nonexistent.sock"):
            assert send_to_running_instance("https://example.com") is False

    def test_sends_data_to_socket(self, tmp_path: Path) -> None:
        """Sends the URL as bytes to a listening Unix socket and returns True."""
        sock_path = tmp_path / "test.sock"
        received: list[bytes] = []

        # Simple echo server.
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(sock_path))
        server.listen(1)

        def _accept() -> None:
            """Accept one connection and record the received data."""
            conn, _ = server.accept()
            with conn:
                received.append(conn.recv(4096))

        t = threading.Thread(target=_accept)
        t.start()

        with patch("flufy.protocol.SOCK_PATH", sock_path):
            result = send_to_running_instance("https://example.com")

        t.join(timeout=2)
        server.close()

        assert result is True
        assert received == [b"https://example.com"]


# ---------------------------------------------------------------------------
# install_desktop_handler
# ---------------------------------------------------------------------------


class TestInstallDesktopHandler:
    """Unit tests for install_desktop_handler()."""

    def test_creates_desktop_file(self, tmp_path: Path) -> None:
        """Desktop file is written with correct MIME type and exec entry."""
        with (
            patch("flufy.protocol.Path.home", return_value=tmp_path),
            patch("flufy.protocol.subprocess.run"),
        ):
            path = install_desktop_handler()

        assert path.exists()
        content = path.read_text()
        assert "x-scheme-handler/slack" in content
        assert "-m flufy %u" in content
