# Changelog

What changed in each release of ryad, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

To release: rename `Unreleased` to the version and date, `## [X.Y.Z] - YYYY-MM-DD`, add a new empty `## [Unreleased]` above it, commit, then run `./release.sh --key=FILE --version=X.Y.Z`, which tags `vX.Y.Z` once every check passed. The date is required: `release.sh` refuses an undated heading. The installer shows these notes on upgrade, and they become the GitHub release notes.


## [Unreleased]

## [0.1.3] - 2026-10-31

A pass over the project before it went public: checks that weren't running, a
report that overstated what it had checked, and documentation that didn't match
the code.

### Changed

- `release.sh` now parses and lints **every** script that ships, not only `ryad`, `bundle.sh` and `installer/stub.sh`. `entrypoint.sh`, `sbin/ryad-setuser`, `apps/*.sh`, `profile.d/*.sh`, `build.sh` and `release.sh` itself are included. The ones with no shebang carry a `shell=bash` directive, so shellcheck knows what it is reading.
- `release.sh` requires the date on a release's changelog heading, `## [X.Y.Z] - YYYY-MM-DD`. It only checked that the section wasn't empty, which is how 0.1.0 to 0.1.2 all went out undated.

### Fixed

- A comment line in `release.sh` that began with the word "shellcheck" parsed as a malformed shellcheck directive, and a malformed directive switches off **every** check in that file. `release.sh` had been passing its own lint without being read.
- `ryad build --check` reported "Up to date." for the image as a whole after comparing Claude Code and Claude Desktop only. The image records no version for the other apps, so they counted as current whatever had been released since. They are now listed as not compared, and the summary says what it actually checked.
- The installer skips manifest lines that point outside the install prefix. `--uninstall` and upgrades removed whatever the manifest named, so a `../..` entry in it reached files outside; the empty-folder cleanup beside it was already guarded that way.
- `docs/security.md` now says that `profile.conf` and `build.conf` are shell scripts run on the host (the shell completion reaches `build.conf` on a `<TAB>`), which app downloads are verified and which rely on TLS alone, and exactly which folders are refused as a workspace. The X11 warning is in `README.md` too: on an X11 desktop, anything in an environment can read every other X11 window.
- `README.md`: the apt-package example was missing the `mkdir -p` it needs on a fresh install, Emacs was described as removable with `ryad apps rm` when it is an apt package, and the environment diagram had a typo and a bottom border one divider short.
- `docs/`: a `ryad --version` sample that `git describe` cannot produce, two `install` commands that fail when `~/.local/bin` doesn't exist yet, a banner app order that didn't match the one the build writes, a `codium` example that said `antigravity`, and `--help` described as printing everything this reference does.
- The 0.1.1 entry below said `ryad-installer.run`, a name 0.1.2 introduced. 0.1.1 shipped `ryad.run`, which is what its published release notes say, and 0.1.2's entry now describes the rename instead of calling it "Minor naming fix".
- The author's name is spelled `Caré` everywhere, including the copyright line of `LICENSE.md`.

## [0.1.2] - 2026-10-30

The installer is named for what it is.

### Changed

- The installer is now `ryad-installer.run`, where 0.1.1 called it `ryad.run`. That old name read like the launcher, which sits beside it in the same release as `ryad`. The newest installer is therefore at `https://github.com/bcare-bergia/ryad/releases/latest/download/ryad-installer.run`, and `SHA256SUMS` lists the new name: update anything that fetched `ryad.run`. Installing and upgrading are otherwise unchanged, `bash ryad-installer.run`.

## [0.1.1] - 2026-10-30

Release files renamed, so downloading the newest one no longer takes a version lookup.

### Changed

- The release files are now `ryad` and `ryad.run`, with no version in their names. The newest installer therefore always sits at the same address, `https://github.com/bcare-bergia/ryad/releases/latest/download/ryad.run`, and the checksums and their signature next to it: no need to find the version number first. To upgrade, download those three and run `bash ryad.run`, as in Getting started. `SHA256SUMS` lists the new names, so checking it works as before.

### Fixed

- `ryad` passes `shellcheck -S warning`, the check `release.sh` runs before every release and which was failing: the `--userns` and `--user` arguments of `podman create` are now quoted, and two local variables that shared a name with an associative array in another function were renamed. Nothing behaves differently.

## [0.1.0] - 2026-10-30

First release with core functionality.

### Added

- Persistent, named sandbox environments (rootless Podman containers), each with one workspace folder and one profile.
- Profiles: separate logins, API keys, history and prompt colors per context.
- Preinstalled apps: Claude Code, Claude Desktop, Pi, Google Antigravity, VSCodium, RStudio, Firefox, Emacs.
- `ryad apps` to list, add, remove and write app installers.
- Single-file bundle (`bundle.sh`), and release installers (`release.sh`).
