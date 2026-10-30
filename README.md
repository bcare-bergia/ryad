<p align="center">
  <img src="art/riad.svg" alt="ryad: an isometric riad on an island at sunset, in ASCII" width="760">
</p>

<h1 align="center">ryad</h1>

<p align="center">
  <b>Sandboxed workspaces for AI agents and LLM tools on Linux.</b><br>
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

LLM-powered tools are most useful when they can act: run commands, install packages, edit files, browse. You probably don't want them doing that **next to your SSH keys, your other projects and the rest of your home directory**.

ryad gives each project its own **environment**: a rootless Podman container that you enter from a terminal and that stays around until you remove it. Inside, an agent can do what it likes (even `sudo apt install`), but it only sees:

- 📁 **one workspace**: your project folder, read-write, at the same path as on the host
- 👤 **one profile**: a private home with your logins, API keys, settings and history

```
 Host                                  Environment "acme"
 ───────────────────────────────       ───────────────────────────────────────
 ~/projects/acme   ─────────────────▶  ~/projects/acme       (read-write)
 ~/.config/ryad/profiles/work/home ─▶  /home/you             (logins, settings)
 Wayland / X11 display ────────────▶   GUI apps open on your desktop

 ~/.ssh, ~/Documents, other projects,
 host keyring, host D-Bus …            ✗ not visible
```

ryad doesn't care which model or vendor you use. It ships with a few agents ready to go, and anything else that runs on Debian or Ubuntu can be added to the image: another agent CLI, a local model client, your own scripts.

A *riad* is a house built around an inner courtyard: open on the inside, walled off from the street.

## What's inside

| | |
|---|---|
| **Agents** | [Pi](https://pi.dev) (`pi`, works with most model providers), Google Antigravity (`antigravity`), Claude Code (`claude`), Claude Desktop (`claude-desktop`) |
| **Editors** | VSCodium, Emacs, RStudio |
| **Browser** | Firefox, for sign-in pages and anything else that needs one |
| **Toolchains** | git, Python, Node.js, R, build-essential, ripgrep… |

GUI apps started inside the sandbox open on your normal Wayland or X11 desktop. Every app except Claude Code and Claude Desktop can be left out, and you can [add your own](docs/customization.md#add-a-third-party-app).

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

The last command creates the environment "acme" and opens a shell in it. From there, start whichever tool you like:

```console
you@acme:~/projects/acme$ pi            # or claude, antigravity, codium …
```

See [Getting started](docs/getting-started.md) for the details.

## Examples

**Keep work and personal accounts apart.** Each profile has its own logins, keys and history.

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
ryad acme -d -- antigravity
ryad -d -- codium .                 # the environment of the current folder
```

**Run a single command** instead of opening a shell:

```bash
ryad acme -- pi -p "list the TODOs in this repository"
```

**Add your own tools to the image:**

```bash
echo "postgresql-client" >> ~/.config/ryad/packages/50-mine.list
ryad build && ryad recreate acme
```

**Upgrade every app** in every environment:

```bash
ryad build && ryad recreate --outdated
```

## Documentation

| Guide | |
|---|---|
| 🚀 [Getting started](docs/getting-started.md) | Requirements, installation, first build, first environment, logging in |
| 🧭 [Usage](docs/usage.md) | Entering environments, starting apps, managing environments day to day |
| 👤 [Profiles](docs/profiles.md) | Logins and API keys, sharing a profile between projects, prompt colors |
| 🎨 [Customization](docs/customization.md) | Adding packages and apps, pinning versions, changing the base image |
| 🔄 [Upgrading](docs/upgrading.md) | Getting new app releases and security updates |
| 🔒 [Security model](docs/security.md) | What is isolated and what isn't |
| 🧱 [Foundations](docs/foundations.md) | How ryad works under the hood, repository layout |
| 📖 [Reference](docs/reference.md) | Every command, option, setting and file |
| 🩺 [Troubleshooting](docs/troubleshooting.md) | Common problems and fixes |
