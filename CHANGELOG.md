# Changelog

What changed in each release of ryad, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

To release: rename `Unreleased` to the version and date, e.g. `## [0.1.0] - 2026-11-02`, commit, tag `v0.1.0`, then run `./release.sh`, which takes the version from that tag. The installer shows these notes on upgrade, and they become the GitHub release notes.

## [Unreleased]

### Added

- Persistent, named sandbox environments (rootless Podman containers), each with one workspace folder and one profile.
- Profiles: separate logins, API keys, history and prompt colors per context.
- Preinstalled apps: Claude Code, Claude Desktop, Pi, Google Antigravity, VSCodium, RStudio, Firefox, Emacs.
- `ryad apps` to list, add, remove and write app installers.
- Single-file bundle (`bundle.sh`), and release installers (`release.sh`).
