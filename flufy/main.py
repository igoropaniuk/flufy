"""CLI entry point for flufy."""

import logging
import logging.handlers
import sys

from flufy.config import APP_NAME, LOG_DIR
from flufy.protocol import (
    deep_link_to_url,
    install_desktop_handler,
    send_to_running_instance,
)

log = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Set up logging to stderr (for journald) and a rotating log file."""
    fmt = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # stderr - captured by journald when launched from .desktop
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)
    root.addHandler(stderr_handler)

    # Rotating log file
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{APP_NAME}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Silence noisy Qt internals
    logging.getLogger("PyQt6").setLevel(logging.WARNING)


def main() -> None:
    """Parse arguments and dispatch to the appropriate action."""
    _configure_logging()
    log.info("starting %s (args=%s)", APP_NAME, sys.argv[1:])

    args = sys.argv[1:]

    if "--install" in args:
        path = install_desktop_handler()
        log.info("registered slack:// protocol handler -> %s", path)
        return

    # Handle slack:// deep link passed as first argument.
    if args and args[0].startswith("slack://"):
        uri = args[0]
        if send_to_running_instance(uri):
            log.info("forwarded %s to running instance", uri)
            return

        from flufy.app import run

        run(initial_url=deep_link_to_url(uri))
        return

    # Normal launch: signal existing instance to show, or start a new one.
    if send_to_running_instance("show"):
        log.info("signalled running instance to show")
        return

    from flufy.app import run

    run()


if __name__ == "__main__":
    main()
