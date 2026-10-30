# Getting started

This guide takes you from a fresh checkout to an AI agent working in a sandbox.

- [Requirements](#requirements)
- [Install](#install)
- [Build the image](#build-the-image)
- [Create your first environment](#create-your-first-environment)
- [Sign in to your tools](#sign-in-to-your-tools)
- [Shell completion](#shell-completion)
- [Next steps](#next-steps)

## Requirements

- Linux with rootless **Podman** (tested with Podman 5.7 on Ubuntu 26.04)
- `curl` and `jq` on the host (used by `ryad build`)
- A Wayland or X11 session for the GUI apps. Without one, the terminal apps (`pi`, `claude`, your shell tools) still work.
- An x86-64 or ARM64 machine

## Install

`ryad` is a single file. Install it with the installer of a [release](https://github.com/bcare-bergia/ryad/releases), or make it from this repository.

### From a release

Download `ryad.run`, `SHA256SUMS` and `SHA256SUMS.sig` from the release, check them, then run the installer:

```bash
base=https://github.com/bcare-bergia/ryad/releases/latest/download
curl -fsSL --remote-name-all "$base/ryad.run" "$base/SHA256SUMS" "$base/SHA256SUMS.sig"
curl -fsSL https://github.com/bcare-bergia.keys | sed 's/^/bcare-bergia /' > allowed_signers
ssh-keygen -Y verify -f allowed_signers -I bcare-bergia -n file -s SHA256SUMS.sig < SHA256SUMS
sha256sum --ignore-missing -c SHA256SUMS
bash ryad.run
```

The release files carry no version in their names, so `releases/latest/download/` always points at the newest release: the first two lines download it. The next two check that `SHA256SUMS` was signed with one of the author's SSH keys, as published on GitHub, and the one after checks the installer against it. For an older release, take the same file names from its own page.

The installer shows the license, then installs `ryad` in `~/.local/bin`, its [shell completion](#shell-completion), and these docs in `~/.local/share/doc/ryad`. It never touches your profiles, settings, images or environments. Its options:

| | |
|---|---|
| `--prefix=DIR` | install in `DIR/bin` and `DIR/share` instead of `~/.local` |
| `--yes` | accept the license without asking |
| `--uninstall` | remove what it installed |
| `--list`, `--extract=DIR` | show or write out the files it carries, without installing |

The release also has the plain `ryad` file, if you'd rather copy it onto your `PATH` yourself.

### From this repository

```bash
./bundle.sh                                  # writes dist/ryad
install -m 0755 dist/ryad ~/.local/bin/ryad
ryad --version                               # ryad 0.1.0-3-g95356cf (4e7c8584977f, bundled 2026-10-30)
```

The bundled `dist/ryad` carries the files the image is built from (the Dockerfile, `apps/`, `packages/`…), so `ryad build` works from anywhere without this repository. The version is the release it comes from, from `git describe` (`0.1.0`, or `0.1.0-3-g95356cf` three commits later), followed by a short hash of the bundle's contents: two copies with the same hash are identical.

After changing anything in the repository, run `./bundle.sh` again and reinstall.

> [!NOTE]
> The `ryad` script at the top of the repository is the unbundled source. It does everything except `ryad build`, which needs `--context=DIR` there. `./build.sh` does exactly that.

## Build the image

```bash
ryad build
```

This produces the image `ryad:latest`, also tagged with the versions it contains. It picks the latest release of each app. The first build downloads a few GB and takes a while; later builds only redo the layers that changed.

From a checkout, `./build.sh` does the same with the repository's files. It takes the same options (`./build.sh --help`).

To change what goes into the image, see [Customization](customization.md).

## Create your first environment

Go to a project folder and run `ryad`:

```console
$ cd ~/projects/acme
$ ryad
you@acme:~/projects/acme$
```

This creates an environment named after the folder ("acme"), with the profile `default`, and opens a shell in it. The banner lists the apps you can start:

| Command | App |
|---|---|
| `pi` | Pi, a terminal coding agent that works with most model providers |
| `antigravity` | Google Antigravity |
| `claude` | Claude Code, in the terminal |
| `claude-desktop` | Claude Desktop |
| `codium` | VSCodium (`codium .` opens the workspace) |
| `rstudio` | RStudio |
| `emacs` | Emacs |
| `firefox` | Firefox |

Use any of them, or none: the environment is a normal Linux shell. `ryad apps` lists the apps; you can [remove some, or add your own](customization.md#choose-the-apps).

To use another profile, say one for your work account, pass it the first time:

```bash
ryad --profile=work
```

The environment keeps that profile from then on. See [Usage](usage.md) for everything else you can do with environments.

## Sign in to your tools

You sign in **once per profile**. Every environment using that profile shares the login. Sign-in pages open in the sandbox's Firefox.

- **Pi:** run `pi`, then `/login` to use a subscription, or give it an API key (below).
- **Google Antigravity:** run `antigravity`, then sign in with your Google account.
- **Claude Code:** run `claude`, then `/login`.
- **Claude Desktop:** run `claude-desktop`, then sign in.

API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`…) and cloud-provider settings go in the profile's `profile.env`, where every tool in its environments sees them. See [Profiles](profiles.md#environment-variables-profileenv).

## Shell completion

Bash completion covers subcommands, environment and profile names, options, `--display=` modes, `--image=` images and `--workspace=` folders.

The [installer](#from-a-release) sets it up. Otherwise, load it from `~/.bashrc`:

```bash
source <(ryad completion bash)
```

or install it for the bash-completion package, which loads it on first use:

```bash
mkdir -p ~/.local/share/bash-completion/completions
ryad completion bash > ~/.local/share/bash-completion/completions/ryad
```

**zsh** can use the same script through its bash-compatibility layer. In `~/.zshrc`:

```zsh
autoload -U +X compinit && compinit
autoload -U +X bashcompinit && bashcompinit
source <(ryad completion bash)
```

## Next steps

- [Usage](usage.md): more terminals, background apps, managing environments
- [Profiles](profiles.md): separate accounts, API keys, prompt colors
- [Security model](security.md): know what the sandbox does and doesn't protect
