# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-04-07

### Added

- Browser engine with Chrome User-Agent spoofing to pass Slack's browser check
- System tray icon with unread message monitoring via DOM polling
- Desktop notifications via `notify-send`
- `slack://` deep-link protocol handler for magic login links
- Single-instance enforcement via Unix domain socket IPC
- Persistent sessions (cookies survive restarts)
- User-configurable settings via TOML config file (`~/.config/flufy/config.toml`)
- Auto-generated `.desktop` file and protocol handler registration on first launch
- JS navigator overrides to improve Slack compatibility
- GitHub Actions CI workflow with markdown linter and conventional commits check
- Interactive release script for tagging, building, and publishing to PyPI
