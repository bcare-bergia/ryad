# Security model

ryad's goal is narrow: keep what Claude (and anything it runs) can **see and change** limited to the project you are working on. It is not a network firewall, and it doesn't protect you from a malicious image.

- [At a glance](#at-a-glance)
- [Filesystem](#filesystem)
- [Credentials](#credentials)
- [Processes and privileges](#processes-and-privileges)
- [Network](#network)
- [Display](#display)
- [Electron apps](#electron-apps)
- [Not available: Cowork](#not-available-cowork)

## At a glance

| | Inside an environment |
|---|---|
| The workspace folder | ✅ read-write |
| The profile's home | ✅ read-write |
| The rest of your home: `~/.ssh`, other projects, documents… | ❌ not visible |
| Host keyring, host D-Bus session | ❌ not visible |
| Root on the host | ❌ container root maps to your unprivileged user |
| `sudo` inside the environment | ✅ passwordless, confined to the container |
| Internet, your LAN, services on the host | ⚠️ reachable, not restricted |
| Your display | ⚠️ GUI apps connect to Wayland, and to X11 if you have it |

## Filesystem

An environment sees the workspace, the profile home and the container's own filesystem. Nothing else from your home is mounted.

- The launcher refuses to mount `/` or `$HOME` as the workspace unless you pass `--allow-unsafe-workspace`.
- Files created in the workspace belong to your host user.
- Everything in the workspace is readable and writable by Claude. Keep secrets you don't want it to see outside the workspace.

## Credentials

Credentials are stored **unencrypted** in the profile folder, which is mode 0700 on the host:

- Claude Code's `~/.claude/.credentials.json`
- the keyring holding Claude Desktop's sign-in, `~/.local/share/keyrings/login.keyring`. This keyring has no password, so it never prompts.
- anything you put in `profile.env`, such as an API key

Treat `~/.config/ryad/profiles/` like `~/.ssh`.

Profiles also separate accounts from each other: an environment on profile `personal` can't see the logins of profile `work`.

## Processes and privileges

- Each environment is a rootless Podman container with its own PID, IPC and user namespaces.
- Container root maps to your own unprivileged user on the host.
- The user inside has passwordless `sudo`, so Claude can install tools. Those changes stay inside that environment's container and disappear when it is recreated.
- SELinux labelling is disabled for the container (`--security-opt label=disable`), so that the workspace and display sockets can be shared without relabelling them.
- By default, `/dev/dri` is passed in for GPU rendering. `--no-gpu` leaves it out.

## Network

**Network access is not restricted.** Claude, the apps and anything they run have normal internet access. They can also reach services on your LAN, and services on the host through the container network gateway.

If that matters for a project, add your own restrictions at the Podman or firewall level, or route traffic through a proxy with `HTTPS_PROXY` in [`profile.env`](profiles.md#environment-variables-profileenv).

## Display

GUI apps connect to your Wayland compositor and, when your session has one, to X11 (including XWayland).

X11 clients can observe each other: an X11 app in the sandbox can read the keystrokes and screen content of other X11 apps on your desktop. Wayland isolates clients from each other.

> [!WARNING]
> `--display=wayland` makes apps prefer Wayland, but the X11 socket is still passed in when your session has one, so that apps without Wayland support keep working. It reduces X11 use; it doesn't remove X11 access.

## Electron apps

Claude Desktop, VSCodium and RStudio are started through small wrappers in the image, in `/usr/local/bin`. The wrappers:

- store secrets in the profile keyring (`--password-store=gnome-libsecret`). There's no desktop environment in the container, so without this Claude Desktop would fall back to an unprotected store and not keep you signed in.
- allow one instance per profile (see [Profiles](profiles.md#sharing-a-profile-between-environments)).
- keep Chromium's own sandbox on. It works in rootless Podman. If an app crashes at startup on your system, run it with `RYAD_ELECTRON_NO_SANDBOX=1` to add `--no-sandbox`.

## Not available: Cowork

Cowork needs KVM (`/dev/kvm`, `/dev/vhost-vsock`), which is deliberately not passed in. Chat and Code in Claude Desktop work.
