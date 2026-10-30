<p align="center">
  <img src="art/riad.svg" alt="ryad: an isometric riad on an island at sunset, in ASCII" width="760">
</p>

<h1 align="center">ryad</h1>

<p align="center">
  <b>Same tools, separate rooms.</b><br>
  A calm way to use LLM-powered tools on Linux, one project at a time.
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

I work on quite a few different things: my own projects, and jobs for a handful of clients. I use LLM-powered tools for all of them (coding agents, chat apps, an editor or two), and I wanted two things that don't naturally go together:

- the **same tools everywhere**, set up once, not reinstalled for every project;
- each project kept **properly apart**. Client X's code, accounts and API keys have no business being near client Y's, and neither should be anywhere near my personal stuff.

On top of that, these tools like to get their hands dirty: they run commands, install packages, edit files. That's what makes them useful, but I'd rather they did it somewhere other than my whole home directory.

So ryad gives each project its own **environment**, a small Podman container you step into from a terminal. Every environment is built from the same image, so your tools are always there. And each one only sees two things:

- its **project folder**, where the work happens;
- a **profile**: a home directory holding the logins, API keys and history for one context. One for your personal projects, one per client, or whatever split suits you.

Your SSH keys, your documents and your other projects stay outside.

```
      one image, the same tools in every room: pi, claude, codium, git…
 ┌──────────────────────┬──────────────────────┬──────────────────────┐
 │ environment "blog"   │ environment "x-api"  │ environment "y-site" │
 │ ~/perso/blog         │ ~/clients/x/api      │ ~/clients/y/site     │
 │ profile: personal    │ profile: client-x    │ profile: client-y    │
 └──────────────────────┴──────────────────────┴──────────────────────┘
   none of them sees ~/.ssh, ~/Documents, or the others
```

It doesn't matter which model or vendor you use. A few tools come preinstalled, and anything else that runs on Debian or Ubuntu can be added.

A *riad* is a traditional house built around an inner courtyard: open on the inside, walled off from the street. That felt about right.

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

**Keep clients apart.** Each profile has its own logins, keys and history.

```bash
cd ~/clients/x/api  && ryad --profile=client-x
cd ~/clients/y/site && ryad --profile=client-y
cd ~/perso/blog     && ryad --profile=personal
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
