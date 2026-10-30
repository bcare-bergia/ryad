# Usage

Day-to-day use of ryad: entering environments, starting apps, and managing environments over time.

- [Entering an environment](#entering-an-environment)
- [Starting apps](#starting-apps)
- [Creating environments](#creating-environments)
- [Changing an environment's settings](#changing-an-environments-settings)
- [Managing environments](#managing-environments)
- [What survives what](#what-survives-what)

For the full list of commands and options, see the [Reference](reference.md).

## Entering an environment

```
ryad [NAME] [options] [-- CMD [ARGS...]]
```

This one command does everything:

1. **Finds the environment.** Without `NAME`, it uses the environment of the current folder, or of the closest parent folder. So `ryad` in `~/projects/acme/src` enters "acme". If there is none, it creates one named after the folder.
2. **Creates it if needed.** If `NAME` doesn't exist, it asks before creating it for the current folder and suggests close names (`did you mean: acme?`). This guards against typos. `--workspace=DIR` or `--yes` skips the question.
3. **Starts it** if it is stopped.
4. **Opens a login shell** in the current folder if that folder is inside the workspace, otherwise at the top of the workspace.

```console
$ cd ~/projects/acme/src
$ ryad
ryad 'acme' · profile work · workspace /home/you/projects/acme
  claude  claude-desktop  codium  rstudio  emacs  firefox
you@acme:~/projects/acme/src$
```

**More terminals.** Run the same command in another terminal to get another shell in the same environment. `ryad acme` works from any folder. Open as many as you like.

**One command instead of a shell.** Put it after `--`:

```bash
ryad acme -- claude --resume
ryad acme -- git status
```

**Exiting.** Leaving a shell (`exit`) doesn't stop anything. The environment and the apps running in it stay up until you stop it with `ryad stop`.

## Starting apps

From any shell in the environment, run the apps like normal programs: `claude`, `claude-desktop`, `codium`, `rstudio`, `emacs`, `firefox`.

**GUI apps stay in the foreground** of the terminal you start them from, until their window is closed. This includes `codium`, which normally returns straight away: here it stays in the foreground so that the [one-instance-per-profile lock](profiles.md#sharing-a-profile-between-environments) is held while it runs. To get the terminal back, use `claude-desktop &`.

**Starting an app from the host.** Use `--detach` (`-d`) to start an app in the background and get the terminal back:

```bash
ryad acme -d -- claude-desktop
ryad -d -- codium .            # environment of the current folder
```

The app keeps running after you close the terminal. Its output goes to `~/.cache/ryad/logs/<command>.log` in the profile, and the launcher prints that path. If the command fails right away, for example because Claude Desktop is already open in another environment on the same profile, the launcher shows its output and exits with an error.

> [!TIP]
> `ryad -d -- claude-desktop` makes a good desktop shortcut or keyboard binding.

## Creating environments

An environment is created the first time you enter it. The options below only matter at that moment:

| Option | |
|---|---|
| `-w`, `--workspace=DIR` | folder to mount (default: current directory) |
| `-p`, `--profile=NAME` | profile to use (default `default`) |
| `--image=IMAGE` | image (default `ryad:latest`) |
| `--display=auto\|wayland\|x11` | how GUI apps connect to your display |
| `--user=NAME` | user name inside, with home `/home/NAME` (default: your host user name) |
| `--hostname=NAME` | hostname inside (default: the environment name) |
| `--no-gpu` | don't pass `/dev/dri` (try this if a GUI app renders a black window) |
| `--allow-unsafe-workspace` | allow `/` or your home directory as the workspace |

Option values go after `=` or a space: `--profile=work`, `--profile work`, or `-p work`. A profile can also set defaults for these; see [Profiles](profiles.md#creation-defaults-and-prompt-colors-profileconf).

**Naming.** `NAME` defaults to the workspace folder's name, lowercased. If that name is already used by an environment for a *different* folder, the launcher asks you to choose a name instead. Names can't be subcommands or their aliases (`ls`, `remove`, `delete`, `enter`, `start`, `shell`).

**Nested folders.** Without `NAME`, a folder inside an environment's workspace belongs to that environment, and the deepest one wins. With `--profile=X`, only environments on profile X count. For example, `ryad --profile=work` in `acme/src`, where "acme" is on another profile, creates a new environment "src". To create a nested environment on purpose, name it: `ryad src --workspace=.`.

**Several at once.** You can run several environments at the same time, including several on the same profile, for example two projects on your "work" subscription.

**User and home.** Inside, you are UID 1000, mapped to your own user on the host, and named after your host user unless you pick another name with `--user`. The profile's `home/` is mounted as `/home/<user>`. If the workspace is under your host home, e.g. `/home/you/projects/acme`, the prompt shows it as `~/projects/acme` as on the host. Podman creates the empty mount-point folders (`projects/acme`) inside the profile's `home/`. Environments created before `--user` existed keep the name `claude` when recreated.

**Display.** With `--display=auto`, the launcher picks Wayland if your session has it, else X11, else no display. It warns you when you later enter the environment from a session that doesn't match, and prints the `recreate` command that fixes it.

## Changing an environment's settings

An environment's settings are fixed when it is created and stored with it. That is what lets you enter it by name from any directory. Asking for a different profile or workspace for an existing name is an error.

To change a setting, recreate the environment:

```bash
ryad info acme                      # current settings
ryad recreate acme --user=dev
ryad recreate acme --profile=work
ryad recreate acme --display=x11
```

`recreate` shows what changes and asks before going ahead. It builds the new container first, so if that fails (bad `--image`, no display…) the old one is left as it was.

`recreate` without options moves the environment onto the current image, which is how you [upgrade](upgrading.md).

## Managing environments

| Command | |
|---|---|
| `ryad list` (`ls`) | environments with their state, profile, workspace and image. `*` marks an older build |
| `ryad info [NAME]` | an environment's settings (default: the one of the current folder) |
| `ryad stop NAME…` / `--all` | stop; `ryad NAME` starts it again |
| `ryad rm NAME… [--force]` | delete the environment. The profile and workspace are untouched. `--force` stops running ones first |
| `ryad recreate NAME [options]` | recreate on the current image, or with other settings |
| `ryad recreate --outdated` / `--all` | recreate every environment on an older build / every environment, after one confirmation |
| `ryad versions [NAME]` | app versions in an environment's image |

Commands that delete something ask first; `--yes` (`-y`) skips the question. Options that don't apply to a command are refused, not ignored.

## What survives what

| | `exit` | `stop`, then start | `recreate` | `rm` |
|---|:---:|:---:|:---:|:---:|
| Running apps | ✅ | ❌ | ❌ | ❌ |
| Tools installed with `sudo apt install` | ✅ | ✅ | ❌ | ❌ |
| Profile (logins, settings, history) | ✅ | ✅ | ✅ | ✅ |
| Workspace | ✅ | ✅ | ✅ | ✅ |

A stopped environment keeps its container filesystem. `recreate` and `rm` discard it. To keep a tool across recreates, [add it to the image](customization.md).
