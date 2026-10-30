# Troubleshooting

- [A GUI app doesn't appear](#a-gui-app-doesnt-appear)
- ["could not start" after logging out and back in](#could-not-start-after-logging-out-and-back-in)
- ["… is already running in environment 'X'"](#-is-already-running-in-environment-x)
- [A desktop app asks you to sign in every time](#a-desktop-app-asks-you-to-sign-in-every-time)
- ["image not found"](#image-not-found)
- ["this ryad has no embedded build files"](#this-ryad-has-no-embedded-build-files)
- [A tool I installed is gone](#a-tool-i-installed-is-gone)
- [Getting more information](#getting-more-information)

## A GUI app doesn't appear

1. Read its output in the terminal you started it from. For an app started with `-d`, the launcher printed the path of its log.
2. Check for a display warning when you entered the environment. If it was created without a display (e.g. over SSH), or for Wayland and you are now in an X11-only session, run the `recreate` command it suggests.
3. Try X11 or no GPU: `ryad recreate NAME --display=x11`, or `ryad recreate NAME --no-gpu` if the window is black.
4. If it crashes mentioning the sandbox, start it with `RYAD_ELECTRON_NO_SANDBOX=1`, e.g. `RYAD_ELECTRON_NO_SANDBOX=1 ryad acme -- antigravity`.

## "could not start" after logging out and back in

The launcher refreshes its display links in `$XDG_RUNTIME_DIR/ryad/` before every start, so a new login is normally fine. If your display setup changed (Wayland ↔ X11), or the workspace folder was moved or deleted, run `ryad recreate NAME`.

## "… is already running in environment 'X'"

Another environment on the same profile has that app open. Desktop apps (Antigravity, Claude Desktop, VSCodium, RStudio) can run in only one environment per profile at a time. Close it there, or give this environment its own profile. See [Profiles](profiles.md#sharing-a-profile-between-environments).

## A desktop app asks you to sign in every time

Its secret storage isn't reaching the keyring. Inside the environment:

- Check that `secret-tool search --all service x` runs without error.
- Make sure you start the app by its usual command (`antigravity`, `claude-desktop`, `codium`…), i.e. through the wrapper in `/usr/local/bin`.
- For Claude Desktop, look for `safeStorage … backend=basic_text` in `~/.config/Claude/logs/main.log`.

## "image not found"

The environment's image doesn't exist (yet). Run `ryad build`, or `ryad recreate NAME --image=…` to move the environment to an existing image.

## "this ryad has no embedded build files"

You are running the unbundled `ryad` from the repository. Use `./build.sh`, or install the bundle (see [Getting started](getting-started.md#install)).

## A tool I installed is gone

Tools installed with `sudo apt install` inside an environment live in its container filesystem, which `recreate` discards. Add them to the image instead: [a package list](customization.md#add-apt-packages) for distro packages, `ryad apps new` for [anything else](customization.md#add-a-third-party-app).

## Getting more information

| | |
|---|---|
| `ryad info NAME` | the environment's settings |
| `ryad versions NAME` | what its image contains, and whether it is outdated |
| `podman logs ryad-NAME` | the container's own log (entrypoint, D-Bus, keyring) |
| `~/.cache/ryad/logs/` | output of apps started with `--detach`, in the profile home |
