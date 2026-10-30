# Foundations

How ryad works under the hood. You don't need any of this to use it; it helps when you customize the build files, debug a problem, or want to check the [security model](security.md) for yourself.

- [Overview](#overview)
- [The launcher](#the-launcher)
- [The image](#the-image)
- [Inside a running environment](#inside-a-running-environment)
- [Display plumbing](#display-plumbing)
- [Electron app wrappers](#electron-app-wrappers)
- [Bundling and versions](#bundling-and-versions)
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

The [Dockerfile](../Dockerfile) builds the image in layers ordered from least to most frequently changing, so that upgrading Claude only rebuilds the last two:

| # | Layer | Comes from | Rebuilt when |
|---|---|---|---|
| 1 | apt packages | `packages/*.list`, `EXTRA_PACKAGES` | a list changes, or `--refresh` |
| 2 | user account | UID 1000, passwordless sudo | rarely |
| 3 | third-party apps | `apps/<name>.sh`, for each app in `APPS` | an app or its version changes |
| 4 | Claude Desktop | `apps/claude-desktop.sh` | a new Desktop version |
| 5 | Claude Code | `apps/claude-code.sh` | a new Code version |

Before building, `ryad build` resolves `latest` and `stable` into concrete version numbers and passes them as build arguments. A rebuild therefore invalidates exactly the layers whose version changed. The resolved versions also give the image its tag, `cc-<code>_cd-<desktop>`, and are recorded as image labels and in `/etc/ryad-release`, which `ryad versions` reads.

Claude Code is installed as the native binary in `/opt/claude-code`, with the same checksum verification as the official installer, but system-wide rather than per user, since the home directory is the profile. Its auto-updater is disabled (`DISABLE_AUTOUPDATER=1`).

## Inside a running environment

The container's main process is [entrypoint.sh](../entrypoint.sh). At each start it:

1. renames the image's user (`claude`) to the name chosen at creation, the first time only ([sbin/ryad-setuser](../sbin/ryad-setuser));
2. seeds an empty profile home from `/etc/skel`;
3. starts a private session D-Bus;
4. starts `gnome-keyring` with an unencrypted, never-locked "login" keyring in the profile, so Claude Desktop can keep its sign-in;
5. then idles until the environment is stopped.

Shells and apps are not children of the entrypoint: each `ryad NAME` adds a process with `podman exec`. That's why closing a terminal doesn't stop the environment.

Login shells show a banner and, if `PROMPT_COLORS` is set, a colored prompt ([profile.d/](../profile.d)).

## Display plumbing

Container mounts are fixed at creation, but the Wayland socket name and the Xauthority file change between logins. The launcher therefore mounts **stable paths** in `$XDG_RUNTIME_DIR/ryad/` on the host and refreshes them before every start and enter:

- `wayland`: a hard link to your session's Wayland socket, mounted as `wayland-0` inside
- `Xauthority`: a copy of your X cookie, rewritten in place so that running containers see updates

`/tmp/.X11-unix` is mounted read-only when your session has X11, in both X11 and Wayland modes. The display mode itself (`auto`, `wayland`, `x11`) is resolved once, at creation, and stored as a label.

## Electron app wrappers

Claude Desktop, VSCodium and RStudio are Electron apps. Their installers call `electron_wrapper` from [apps/lib.sh](../apps/lib.sh), which writes a wrapper in `/usr/local/bin`, ahead of the real binary in `PATH`. Desktop files and deep links (`claude://…`) go through it too. The wrapper:

- adds `--password-store=gnome-libsecret`, so secrets go to the profile keyring;
- adds `--no-sandbox` when `RYAD_ELECTRON_NO_SANDBOX=1`;
- takes a lock, `~/.cache/ryad/<app>.lock`, in the profile home. Environments sharing a profile see the same file, so a second instance in another environment is refused with the name of the one holding it. A second launch in the *same* environment is let through, so the app's own single-instance handling can take it over (that is how sign-in links reach Claude Desktop);
- stays in the foreground until the app's main process exits, even if its launcher returns early (as `codium` does), so the lock is held for as long as the app runs.

## Bundling and versions

[bundle.sh](../bundle.sh) makes `dist/ryad`: the launcher, followed by a marker line and the build files as a base64 `tar.gz`. `ryad build` unpacks them into a temporary folder, adds your files from `~/.config/ryad/`, and runs `podman build` there.

The archive is reproducible (sorted names, fixed owners and timestamps), and the version stamp is the first 12 hex digits of the SHA-256 of the launcher and the archive. Two bundles with the same stamp are byte-for-byte the same build. Each image records the stamp of the bundle that built it (`org.ryad.launcher`), or `source` when built with `--context`.

## Repository layout

```
Dockerfile         image definition (layers: apt lists → user → apps → Claude Desktop → Claude Code)
build.conf         default build settings
ryad               launcher: environments, profiles, and 'ryad build'
bundle.sh          makes dist/ryad: the launcher with the build files embedded
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
