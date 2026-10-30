# Foundations

How ryad works under the hood. You don't need any of this to use it; it helps when you customize the build files, debug a problem, or want to check the [security model](security.md) for yourself.

- [Overview](#overview)
- [The launcher](#the-launcher)
- [The image](#the-image)
- [Inside a running environment](#inside-a-running-environment)
- [Display plumbing](#display-plumbing)
- [Electron app wrappers](#electron-app-wrappers)
- [Bundling and versions](#bundling-and-versions)
- [Releases](#releases)
- [Repository layout](#repository-layout)

## Overview

ryad has three parts:

```
 ┌───────────────┐   ryad build     ┌──────────────┐   ryad NAME     ┌───────────────────────┐
 │ build files   │ ───────────────▶ │ image        │ ──────────────▶ │ environment           │
 │ Dockerfile,   │  (podman build)  │ ryad:latest  │ (podman create, │ container ryad-NAME   │
 │ apps/, …      │                  │              │  start, exec)   │ + workspace + profile │
 └───────────────┘                  └──────────────┘                 └───────────────────────┘
```

- **The launcher** (`ryad`) is a single bash script. It builds the image and manages environments, through Podman.
- **The image** holds the apps and their dependencies. All environments built from it are identical.
- **An environment** is a long-lived Podman container. Its state lives in three places: the container filesystem (lost on recreate), the profile home and the workspace (both kept).

## The launcher

The launcher keeps **no state of its own**. Everything it knows about an environment is stored on the container:

- The container is named `ryad-<name>`.
- Its settings are Podman labels: `org.ryad.name`, `org.ryad.profile`, `org.ryad.workspace`, `org.ryad.image`, `org.ryad.display`, `org.ryad.gpu`, `org.ryad.user`, `org.ryad.hostname`. `ryad info` prints them.

That is why settings are fixed at creation, and why `recreate` is how you change them: it creates a new container with new labels, then swaps it in place of the old one (create aside, remove the old, rename).

When it creates an environment, the launcher runs `podman create` with, in short:

| Flag | Purpose |
|---|---|
| `--userns=keep-id:uid=1000,gid=1000` | your host user is UID 1000 inside, so files in the workspace keep your ownership |
| `-v <profile>/home:/home/<user>` | the profile is the home directory |
| `-v <workspace>:<workspace>` | the workspace, at the same path as on the host |
| `--tmpfs /run/user/1000` | a private `$XDG_RUNTIME_DIR` |
| `--device /dev/dri` | GPU, unless `--no-gpu` |
| display sockets | see [Display plumbing](#display-plumbing) |
| `--init` | a minimal PID 1 that forwards signals, so `ryad stop` is immediate |

Entering an environment is `podman start` (if needed), then `podman exec` of a login shell or your command. `profile.env` and `PROMPT_COLORS` are passed at each `exec`, which is why their edits apply right away.

## The image

The [Dockerfile](../Dockerfile) builds the image in layers ordered from least to most frequently changing. Claude Desktop and Claude Code release almost daily, so they get the last two layers of their own, and their upgrades rebuild only those:

| # | Layer | Comes from | Rebuilt when |
|---|---|---|---|
| 1 | apt packages | `packages/*.list`, `EXTRA_PACKAGES` | a list changes, or `--refresh` |
| 2 | user account | UID 1000, passwordless sudo | rarely |
| 3 | third-party apps, one layer each | `apps/<name>.sh`, for each app in `APPS` | that app, its version, or an app before it changes |
| 4 | Claude Desktop | `apps/claude-desktop.sh` | a new Desktop version |
| 5 | Claude Code | `apps/claude-code.sh` | a new Code version |

`ryad build` writes one layer per app into the Dockerfile it builds from, in place of the block between `# @apps-begin` and `# @apps-end` (which, for a plain `podman build`, installs them all in one layer). The built-in apps come first, in the built-in order, then yours: adding or removing an app only rebuilds the layers after it. `/etc/ryad/apps.list` records the apps with the commands they add, for the shell banner.

Before building, `ryad build` resolves `latest` and `stable` into concrete version numbers and passes them as build arguments. For the other apps, it runs the `# @latest` line of their script, if they have one, in a throwaway container of the previous image. A rebuild therefore invalidates exactly the layers whose version changed. The resolved versions of Claude Code and Claude Desktop also give the image its tag, `cc-<code>_cd-<desktop>`; all resolved versions are recorded as image labels and in `/etc/ryad-release`, which `ryad versions` reads.

Claude Code is installed as the native binary in `/opt/claude-code`, with the same checksum verification as the official installer, but system-wide rather than per user, since the home directory is the profile. Its auto-updater is disabled (`DISABLE_AUTOUPDATER=1`).

## Inside a running environment

The container's main process is [entrypoint.sh](../entrypoint.sh). At each start it:

1. renames the image's user (`claude`) to the name chosen at creation, the first time only ([sbin/ryad-setuser](../sbin/ryad-setuser));
2. seeds an empty profile home from `/etc/skel`;
3. starts a private session D-Bus;
4. starts `gnome-keyring` with an unencrypted, never-locked "login" keyring in the profile, so desktop apps can keep their sign-ins;
5. then idles until the environment is stopped.

Shells and apps are not children of the entrypoint: each `ryad NAME` adds a process with `podman exec`. That's why closing a terminal doesn't stop the environment.

Login shells show a banner and, if `PROMPT_COLORS` is set, a colored prompt ([profile.d/](../profile.d)).

## Display plumbing

Container mounts are fixed at creation, but the Wayland socket name and the Xauthority file change between logins. The launcher therefore mounts **stable paths** in `$XDG_RUNTIME_DIR/ryad/` on the host and refreshes them before every start and enter:

- `wayland`: a hard link to your session's Wayland socket, mounted as `wayland-0` inside
- `Xauthority`: a copy of your X cookie, rewritten in place so that running containers see updates

`/tmp/.X11-unix` is mounted read-only when your session has X11, in both X11 and Wayland modes. The display mode itself (`auto`, `wayland`, `x11`) is resolved once, at creation, and stored as a label.

## Electron app wrappers

Antigravity, Claude Desktop, VSCodium and RStudio are Electron apps. Their installers call `electron_wrapper` from [apps/lib.sh](../apps/lib.sh), which writes a wrapper in `/usr/local/bin`, ahead of the real binary in `PATH`. Desktop files and deep links go through it too. The wrapper:

- adds `--password-store=gnome-libsecret`, so secrets go to the profile keyring;
- adds `--no-sandbox` when `RYAD_ELECTRON_NO_SANDBOX=1`;
- takes a lock, `~/.cache/ryad/<app>.lock`, in the profile home. Environments sharing a profile see the same file, so a second instance in another environment is refused with the name of the one holding it. A second launch in the *same* environment is let through, so the app's own single-instance handling can take it over (that is how sign-in links such as `antigravity://…` and `claude://…` reach the running app);
- stays in the foreground until the app's main process exits, even if its launcher returns early (as `codium` does), so the lock is held for as long as the app runs.

## Bundling and versions

[bundle.sh](../bundle.sh) makes `dist/ryad`: the launcher, followed by a marker line and the build files as a base64 `tar.gz`. `ryad build` unpacks them into a temporary folder, adds your files from `~/.config/ryad/`, and runs `podman build` there.

The archive is reproducible (sorted names, fixed owners and timestamps). `ryad --version` shows two things:

- the **version**: `X.Y.Z` in a release, otherwise `git describe` of the checkout it was bundled from (`0.1.0-3-g95356cf`, `-dirty` with uncommitted changes), or `dev` outside a checkout;
- the **stamp**: the first 12 hex digits of the SHA-256 of the launcher and the archive. Two bundles with the same stamp are byte-for-byte the same build, whatever their version says.

Each image records the version and stamp of the bundle that built it (`org.ryad.launcher`), or `source` when built with `--context`.

## Releases

A release is a git tag `vX.Y.Z` (semantic versioning), its section in [CHANGELOG.md](../CHANGELOG.md), and the files [release.sh](../release.sh) makes from the tagged commit:

| File | |
|---|---|
| `ryad-X.Y.Z` | the bundle |
| `ryad-X.Y.Z.run` | the installer: [installer/stub.sh](../installer/stub.sh), followed by a marker line and a base64 `tar.gz` of the bundle, its bash completion and the docs |
| `SHA256SUMS`, `SHA256SUMS.sig` | checksums of both, signed with an SSH key (`ssh-keygen -Y sign`, namespace `file`) |
| `RELEASE_NOTES.md` | the version's changelog section, for the GitHub release |

To make one:

1. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and add a new, empty `Unreleased` above it. Commit.
2. Try it: `./release.sh --snapshot`, then install the snapshot on a real machine, over the previous release.
3. `./release.sh --key=~/.ssh/KEY --version=X.Y.Z` (or set `RYAD_SIGNING_KEY`). It tags the commit `vX.Y.Z` only once every check passed; if it fails, nothing is tagged: fix, commit and run it again. The key must be one of those listed at `github.com/bcare-bergia.keys`, since that is what users check the signature against.
4. `git push origin main vX.Y.Z`, then `./release.sh --key=~/.ssh/KEY --publish`.
5. Review the draft release on GitHub, then publish it there, or with `gh release edit vX.Y.Z --draft=false`. Once published, a version is final: fix it with a new one.

`./release.sh --help` has the details, including what to check by hand that the script can't.

`release.sh --version=X.Y.Z` builds the current commit with `git archive`, not the working tree (it refuses uncommitted changes to tracked files), with the dates taken from that commit. It checks the version is higher than the last tag, builds everything twice and stops if the two differ, then runs [tests/installer-test.sh](../tests/installer-test.sh) (install, upgrade, a damaged copy, uninstall, in a throwaway `HOME`) and signs. The files land in `dist/release/X.Y.Z/`, and only then does it tag the commit `vX.Y.Z`, locally: a release tag always means every check passed. The tag doesn't change the bytes, so `--publish`, which takes the version from the tag on the current commit, rebuilds exactly the same files, asks, then uploads them with `gh` as a draft release, which only the repository's collaborators can see until it's published.

`./release.sh --snapshot` does the same from the working tree, unsigned, into `dist/release/snapshot/`, to try the installer before releasing.

`--pre-check` runs all of these checks (with `--publish`, its checks too) in a temporary directory and stops there: nothing lands in `dist/`, nothing is tagged or uploaded.

The installer checks the payload's SHA-256 before extracting anything, copies each file next to its destination and renames it over, and records what it installed in `share/ryad/install.manifest` under the prefix. That record is what `--uninstall` removes, and what an upgrade compares against to remove files a newer version no longer has.

## Repository layout

```
Dockerfile         image definition (layers: apt lists → user → apps → Claude Desktop → Claude Code)
build.conf         default build settings
ryad               launcher: environments, profiles, and 'ryad build'
bundle.sh          makes dist/ryad: the launcher with the build files embedded
release.sh         makes the release files from a tag (see Releases)
installer/stub.sh  the installer's script part
tests/             installer test, run by release.sh
CHANGELOG.md       what changed in each release
build.sh           'ryad build' with this folder's build files
entrypoint.sh      in-container init: user name, session D-Bus, keyring
profile.d/         login banner and prompt colors for sandbox shells
sbin/              in-container helper that renames the user (--user)
packages/*.list    apt packages, one per line
apps/*.sh          third-party app installers (apps/lib.sh holds the Electron wrapper)
examples/          derived-image example
art/               the README picture and the script that renders it
docs/              this documentation
```
