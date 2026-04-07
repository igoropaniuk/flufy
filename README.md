# Flufy

Unofficial arch-agnostic thin client for [Slack](https://slack.com), built with
PyQt6 and QtWebEngine.

## Motivation

Slack does not provide a native Linux client for ARM-based laptops. The official
Slack desktop app ships only as an x86_64 Electron binary, leaving users of
ARM64 devices (such as Qualcomm Snapdragon X Elite laptops) without a
first-class experience. Running the x86_64 build through emulation layers is
slow and unreliable.

Flufy solves this by wrapping the Slack web client in a lightweight
QtWebEngine-based browser window that runs natively on any architecture
supported by Qt, including `aarch64` and `x86_64`.

## Features

- Native performance on ARM64 and x86_64 Linux
- Chrome User-Agent spoofing (Slack blocks non-Chrome browsers)
- System tray icon with unread message indicators
- Desktop notifications via `notify-send`
- `slack://` deep-link protocol handler for magic login links
- Single-instance enforcement via Unix domain socket IPC
- Persistent sessions (cookies survive restarts)
- User-configurable settings via TOML config file

## Requirements

- Python 3.12+
- PyQt6 and PyQt6-WebEngine (6.7.0+)
- Linux desktop environment with a system tray
- `notify-send` (libnotify) for desktop notifications
- `libminizip` system library (required by QtWebEngine)

### Installing system dependencies

On Ubuntu/Debian:

```bash
# Ubuntu 24.04+
sudo apt install libminizip1t64

# Ubuntu 22.04 and earlier
sudo apt install libminizip1
```

## Installation

### From PyPI (recommended)

```bash
pipx install flufy

# Or with pip
pip install flufy
```

### From source

```bash
git clone https://github.com/igoropaniuk/flufy.git
cd flufy
poetry install
```

### Post-install

On first launch, Flufy automatically creates a `.desktop` file and registers
the `slack://` protocol handler so it appears in your application launcher and
handles magic login links. To manually re-register if needed:

```bash
flufy --install
```

## Usage

```bash
flufy
```

## Configuration

Flufy reads an optional TOML config file from
`~/.config/flufy/config.toml`. Supported keys:

| Key                  | Type   | Default                         |
|----------------------|--------|---------------------------------|
| `target_url`         | string | `https://app.slack.com/client`  |
| `window_title`       | string | `Flufy`                         |
| `window_width`       | int    | `1200`                          |
| `window_height`      | int    | `800`                           |
| `chrome_full_version`| string | `136.0.7103.114`                |
| `unread_poll_ms`     | int    | `3000`                          |

## Development

```bash
# Install dev dependencies
poetry install

# Run linter and formatter
poetry run ruff check flufy/ tests/
poetry run ruff format flufy/ tests/

# Run type checker
poetry run mypy

# Run tests
poetry run pytest
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.

## Disclaimer

Flufy is an unofficial Slack client and is not affiliated with or endorsed by
Slack Technologies, LLC. Slack is a registered trademark of Slack Technologies,
LLC.
