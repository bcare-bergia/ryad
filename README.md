<p align="center">
  <img src="art/riad.svg" alt="ryad: an isometric riad on an island at sunset, in ASCII" width="760">
</p>

<h1 align="center">ryad</h1>

<p align="center">
  <b>Sandboxed environments for Claude Code and Claude Desktop on Linux.</b><br>
  One folder in, everything else out.
</p>

<p align="center">
  <a href="docs/getting-started.md">Getting started</a> ·
  <a href="docs/usage.md">Usage</a> ·
  <a href="docs/profiles.md">Profiles</a> ·
  <a href="docs/customization.md">Customization</a> ·
  <a href="docs/security.md">Security</a> ·
  <a href="docs/reference.md">Reference</a>
</p>

---

## Why ryad?

Claude is most useful when it can act: run commands, install tools, edit files. You probably don't want it doing that **next to your SSH keys, your other projects and the rest of your home directory**.

ryad gives each project its own **environment**: a rootless Podman container that you enter from a terminal and that stays around until you remove it. Inside, Claude can do what it likes (even `sudo apt install`), but it only sees:

- 📁 **one workspace**: your project folder, read-write, at the same path as on the host
- 👤 **one profile**: a private home with your Claude logins, settings and history

```
 Host                                  Environment "acme"
 ───────────────────────────────       ───────────────────────────────────────
 ~/projects/acme   ─────────────────▶  ~/projects/acme       (read-write)
 ~/.config/ryad/profiles/work/home ─▶  /home/you             (logins, settings)
 Wayland / X11 display ────────────▶   GUI apps open on your desktop

 ~/.ssh, ~/Documents, other projects,
 host keyring, host D-Bus …            ✗ not visible
```

A *riad* is a house built around an inner courtyard: open on the inside, walled off from the street.

## What's inside

| | |
|---|---|
| **Claude Code** | `claude`, the CLI |
| **Claude Desktop** | `claude-desktop`, Chat and Code |
| **Editors** | VSCodium, Emacs, RStudio |
| **Browser** | Firefox, used for `/login` |
| **Toolchains** | git, Python, Node.js, R, build-essential, ripgrep… |

GUI apps started inside the sandbox open on your normal Wayland or X11 desktop.

## Try it

You need Linux with **rootless Podman**, plus `curl` and `jq`.

```bash
# 1. Install: ryad is a single file
./bundle.sh
install -m 0755 dist/ryad ~/.local/bin/ryad

# 2. Build the image (a few GB, takes a while the first time)
ryad build

# 3. Step into a project
cd ~/projects/acme
ryad
```

The last command creates the environment "acme" and opens a shell in it:

```console
you@acme:~/projects/acme$ claude        # log in once with /login, then go
```

See [Getting started](docs/getting-started.md) for the details.

## Examples

**Keep work and personal accounts apart.** Each profile has its own logins and history.

```bash
cd ~/work/billing && ryad --profile=work
cd ~/hobby/game   && ryad --profile=personal
```

**Open another terminal in the same environment**, from any folder:

```bash
ryad acme
```

**Start an app in the background** and get your terminal back:

```bash
ryad acme -d -- claude-desktop
ryad -d -- codium .                 # the environment of the current folder
```

**Run a single command** instead of opening a shell:

```bash
ryad acme -- claude --resume
```

**Add your own tools to the image:**

```bash
echo "postgresql-client" >> ~/.config/ryad/packages/50-mine.list
ryad build && ryad recreate acme
```

**Upgrade Claude** (Code and Desktop) everywhere:

```bash
ryad build && ryad recreate --outdated
```

## Documentation

| Guide | |
|---|---|
| 🚀 [Getting started](docs/getting-started.md) | Requirements, installation, first build, first environment, logging in |
| 🧭 [Usage](docs/usage.md) | Entering environments, starting apps, managing environments day to day |
| 👤 [Profiles](docs/profiles.md) | Logins, sharing a profile between projects, API keys, prompt colors |
| 🎨 [Customization](docs/customization.md) | Adding packages and apps, pinning versions, changing the base image |
| 🔄 [Upgrading](docs/upgrading.md) | Getting new Claude releases and security updates |
| 🔒 [Security model](docs/security.md) | What is isolated and what isn't |
| 🧱 [Foundations](docs/foundations.md) | How ryad works under the hood, repository layout |
| 📖 [Reference](docs/reference.md) | Every command, option, setting and file |
| 🩺 [Troubleshooting](docs/troubleshooting.md) | Common problems and fixes |
