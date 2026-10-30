# Profiles

A **profile** is the private home directory of your environments. It holds your Claude logins, app settings, shell history and git identity. Use one profile per account or context, for example `work` and `personal`.

- [What's in a profile](#whats-in-a-profile)
- [Creating and managing profiles](#creating-and-managing-profiles)
- [Logging in](#logging-in)
- [Sharing a profile between environments](#sharing-a-profile-between-environments)
- [Environment variables: `profile.env`](#environment-variables-profileenv)
- [Creation defaults and prompt colors: `profile.conf`](#creation-defaults-and-prompt-colors-profileconf)
- [Git identity](#git-identity)
- [Removing a profile](#removing-a-profile)

## What's in a profile

Each profile is a folder under `~/.config/ryad/profiles/<name>/`, with mode 0700:

```
~/.config/ryad/profiles/work/
├── home/          # mounted as /home/<user>: ~/.claude, ~/.claude.json, ~/.config/Claude,
│                  # the keyring, VSCodium/RStudio/Emacs settings, .gitconfig, history
├── profile.env    # optional: environment variables for its environments
└── profile.conf   # optional: creation defaults and prompt colors for its environments
```

An environment uses exactly one profile, chosen when it is created (`--profile=NAME`, default `default`).

> [!IMPORTANT]
> Credentials are stored unencrypted in `home/`. Treat `~/.config/ryad/profiles/` like `~/.ssh`. See the [Security model](security.md#credentials).

## Creating and managing profiles

A profile is created on first use, or ahead of time with `ryad profiles create`, so you can fill in its settings before creating environments. Either way it comes with commented `profile.conf` and `profile.env` templates. When a profile is created on first use, the launcher reminds you to review them and to run `ryad recreate NAME` to apply them.

| Command | |
|---|---|
| `ryad profiles` | each profile with its environments and whether Claude Code is logged in |
| `ryad profiles create NAME` | create it with the commented templates |
| `ryad profiles edit NAME [conf\|env]` | open `profile.conf` (default) or `profile.env` in `$VISUAL`/`$EDITOR`. Creates the profile if needed |
| `ryad profiles path NAME` | print its folder, e.g. `cd "$(ryad profiles path work)"` |
| `ryad profiles rm NAME…` | delete it (see [below](#removing-a-profile)) |

## Logging in

Log in once per profile, from a shell in any environment that uses it:

- **Claude Code:** `claude`, then `/login`. The login page opens in the sandbox's Firefox. The credentials go to `home/.claude/.credentials.json`.
- **Claude Desktop:** `claude-desktop`, then sign in. The sign-in goes to the profile's keyring, `home/.local/share/keyrings/`.

`ryad profiles` shows, for each profile, whether Claude Code is logged in, or configured through `profile.env`.

## Sharing a profile between environments

Environments on the same profile share its home **live**: logins, settings, Claude Code history and memory.

- **Claude Code** works in all of them at once.
- **Claude Desktop, VSCodium and RStudio** keep their data in a settings folder that only one running copy may use. Each of them can run in **only one environment per profile at a time**. Starting a second copy elsewhere is refused:

  ```
  claude-desktop is already running in environment 'acme', which uses the same profile.
  ```

  Close it there, or give the other environment its own profile.

## Environment variables: `profile.env`

`KEY=value` lines, passed to every shell and app in the profile's environments. Use it for an API key or a cloud provider instead of a subscription, or for a proxy:

```bash
ANTHROPIC_API_KEY=sk-ant-...
# CLAUDE_CODE_USE_BEDROCK=1
# AWS_REGION=eu-west-1
# HTTPS_PROXY=http://proxy:3128
```

Edit it with `ryad profiles edit work env`. It is read each time you enter an environment, so new shells and apps pick up changes right away.

> [!NOTE]
> Environments created by older versions of ryad also got `profile.env` baked in at creation. A variable you *remove* from the file stays set in them until you recreate them.

## Creation defaults and prompt colors: `profile.conf`

Settings in shell syntax. Edit it with `ryad profiles edit work`.

```bash
IMAGE=my-ryad
DISPLAY_MODE=x11
GPU=0
USER_NAME=dev                # default: your user name on the host
HOST_NAME=work-box           # default: the environment name
PROMPT_COLORS="user=bold-red host=yellow dir=bold-blue"
```

| Setting | Same as | Applies |
|---|---|---|
| `IMAGE` | `--image` | at creation |
| `DISPLAY_MODE` | `--display` | at creation |
| `GPU=0` | `--no-gpu` | at creation |
| `USER_NAME` | `--user` | at creation |
| `HOST_NAME` | `--hostname` | at creation |
| `PROMPT_COLORS` | | each time you enter |

Creation defaults apply to new environments. For existing ones, run `ryad recreate NAME`. Options on the command line win over the profile.

### Prompt colors

`PROMPT_COLORS` colors the three parts of the bash prompt, `user@host:dir$`. A red prompt for the `work` profile, for instance, tells you at a glance which account you are on.

Each part takes:

- a color name: `black` `red` `green` `yellow` `blue` `magenta` `cyan` `white`, optionally as `bright-<color>` and/or with a `bold-` prefix (`bold-bright-cyan`), or `default`
- or raw ANSI codes, as in `LS_COLORS`: `dir=1;34`, or a 256-color palette entry with `38;5;N`: `host=1;38;5;161` (bold deep pink)

Parts you leave out keep Ubuntu's colors. Without `PROMPT_COLORS`, the prompt from the profile's `~/.bashrc` is left alone. When it is set, it replaces any `PS1` set in `~/.bashrc`.

To try colors for one shell:

```bash
RYAD_PROMPT_COLORS="user=green" ryad acme
```

## Git identity

The profile has its own `~/.gitconfig`, separate from the host's. Set your name and email once, inside any environment on the profile:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Removing a profile

1. Remove its environments: `ryad rm NAME…`
2. Remove the profile: `ryad profiles rm <name>`. It asks for confirmation; `--yes` skips it.

This deletes its logins, settings and history, including files created by other users inside the sandbox (e.g. with `sudo`).
