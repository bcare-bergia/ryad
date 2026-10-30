# Getting started

This guide takes you from a fresh checkout to Claude running in a sandbox.

- [Requirements](#requirements)
- [Install](#install)
- [Build the image](#build-the-image)
- [Create your first environment](#create-your-first-environment)
- [Log in to Claude](#log-in-to-claude)
- [Shell completion](#shell-completion)
- [Next steps](#next-steps)

## Requirements

- Linux with rootless **Podman** (tested with Podman 5.7 on Ubuntu 26.04)
- `curl` and `jq` on the host (used by `ryad build`)
- A Wayland or X11 session for the GUI apps. Without one, the terminal apps (Claude Code included) still work.
- An x86-64 or ARM64 machine

## Install

`ryad` is a single file. Make it from this repository, then copy it anywhere on your `PATH`:

```bash
./bundle.sh                                  # writes dist/ryad
install -m 0755 dist/ryad ~/.local/bin/ryad
ryad --version                               # ryad f9d05fd960b1 (bundled 2026-10-30)
```

The bundled `dist/ryad` carries the files the image is built from (the Dockerfile, `apps/`, `packages/`…), so `ryad build` works from anywhere without this repository. The version is a short hash of the bundle's contents: two copies with the same version are identical.

After changing anything in the repository, run `./bundle.sh` again and reinstall.

> [!NOTE]
> The `ryad` script at the top of the repository is the unbundled source. It does everything except `ryad build`, which needs `--context=DIR` there. `./build.sh` does exactly that.

## Build the image

```bash
ryad build
```

This produces the image `ryad:latest`, also tagged `ryad:cc-<code-version>_cd-<desktop-version>`. It picks the latest releases of Claude Code and Claude Desktop. The first build downloads a few GB and takes a while; later builds only redo the layers that changed.

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
| `claude` | Claude Code CLI |
| `claude-desktop` | Claude Desktop |
| `codium` | VSCodium (`codium .` opens the workspace) |
| `rstudio` | RStudio |
| `emacs` | Emacs |
| `firefox` | Firefox |

To use another profile, say one for your work account, pass it the first time:

```bash
ryad --profile=work
```

The environment keeps that profile from then on. See [Usage](usage.md) for everything else you can do with environments.

## Log in to Claude

You log in **once per profile**. Every environment using that profile shares the login.

- **Claude Code:** run `claude`, then `/login`. The login page opens in the sandbox's Firefox.
- **Claude Desktop:** run `claude-desktop`, then sign in.

To use an API key or a cloud provider (Bedrock, Vertex) instead of a subscription, put it in the profile's `profile.env`. See [Profiles](profiles.md#environment-variables-profileenv).

## Shell completion

Bash completion covers subcommands, environment and profile names, options, `--display=` modes, `--image=` images and `--workspace=` folders.

Load it from `~/.bashrc`:

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
