# Reference

Every command, option, setting and file, in one place. For explanations, follow the links to the guides. `ryad --help` and `ryad build --help` print the same information in the terminal.

- [Commands](#commands)
- [Options](#options)
- [Build options](#build-options)
- [Settings files](#settings-files)
- [Environment variables](#environment-variables)
- [Files and locations](#files-and-locations)

## Commands

### Environments

| Command | |
|---|---|
| `ryad [NAME] [options]` | enter NAME: create it if needed, start it if stopped, open a shell ([Usage](usage.md#entering-an-environment)) |
| `ryad [NAME] [options] -- CMD [ARGS…]` | same, but run CMD instead of a shell |
| `ryad [NAME] -d -- CMD [ARGS…]` | start CMD in the background and return |
| `ryad list [-q]` | list environments; `*` marks an older build. `-q`: names only |
| `ryad info [NAME]` | settings of an environment (default: the one of the current folder) |
| `ryad stop NAME… \| --all` | stop environments |
| `ryad rm NAME… [--force]` | delete environments (profile and workspace are kept) |
| `ryad recreate NAME [options]` | recreate on the current image, or with other settings |
| `ryad recreate --outdated \| --all` | recreate several environments at once |
| `ryad versions [NAME \| --image=IMAGE]` | app versions in an image (default `ryad:latest`) |

### Apps

| Command | |
|---|---|
| `ryad apps [list] [-q]` | the apps: installed, available, or changing at the next build. `-q`: names only ([Customization](customization.md#choose-the-apps)) |
| `ryad apps add APP… [--yes]` | add apps (saved in `build.conf`), then offer to rebuild and recreate. `--yes`: do it without asking |
| `ryad apps rm APP… [--yes]` | remove apps, the same way |
| `ryad apps new APP` | write `~/.config/ryad/apps/APP.sh` from a template (or from the built-in one of that name) in `$EDITOR` |

### Profiles

| Command | |
|---|---|
| `ryad profiles [list]` | profiles, their environments, and whether Claude Code is set up |
| `ryad profiles create NAME` | create a profile with commented templates |
| `ryad profiles edit NAME [conf\|env]` | edit `profile.conf` (default) or `profile.env` |
| `ryad profiles path NAME` | print the profile's folder |
| `ryad profiles rm NAME… [--yes]` | delete profiles (no environment may use them) |

### Image and tooling

| Command | |
|---|---|
| `ryad build [options]` | build the image ([Build options](#build-options)) |
| `ryad prune [--yes]` | remove ryad images no container uses, except `:latest` |
| `ryad --version` | its version and bundle hash |
| `ryad completion bash` | print the bash completion script |

### Aliases

| Alias | Command |
|---|---|
| `ls` | `list` |
| `remove`, `delete` | `rm` |
| `enter`, `start`, `shell` | `ryad NAME` |

## Options

Values go after `=` or a space: `--profile=work`, `--profile work`, `-p work`. Options that don't apply to a command are refused.

### When creating an environment

These are fixed afterwards; use `recreate` to change them.

| Option | Default | |
|---|---|---|
| `-p`, `--profile=NAME` | `default` | profile: logins, keys and settings |
| `-w`, `--workspace=DIR` | current directory | folder mounted read-write |
| `--image=IMAGE` | `ryad:latest` | image |
| `--display=MODE` | `auto` | `auto`, `wayland` or `x11` |
| `--user=NAME` | your host user name | user name inside, home `/home/NAME` |
| `--hostname=NAME` | the environment name | hostname inside |
| `--no-gpu` | | don't pass `/dev/dri` |
| `--allow-unsafe-workspace` | | allow `/` or your home directory as workspace |

### Other options

| Option | |
|---|---|
| `-y`, `--yes` | don't ask for confirmation |
| `-f`, `--force` | `rm`: stop running environments first (same as `--yes`) |
| `-d`, `--detach` | start CMD in the background |
| `-q`, `--quiet` | `list`: names only |

## Build options

`ryad build [options]`, or `./build.sh [options]` in the repository. See [Customization](customization.md).

| Option | |
|---|---|
| `--check` | show built vs available versions, don't build |
| `--refresh` | rebuild the apt layer (pull distro security updates) |
| `--no-cache` | rebuild every layer |
| `--code-version=V` | Claude Code: `latest`, `stable` or `X.Y.Z` |
| `--desktop-version=V` | Claude Desktop: `latest` or `X.Y.Z` |
| `--rstudio-version=V` | RStudio: `latest` or `X.Y.Z-N` |
| `--apps="a b c"` | apps for this build only, as in `APPS` (`a b`, `+a -b`). To keep a change, use `ryad apps add/rm` |
| `--packages="p1 p2"` | extra apt packages, added to `EXTRA_PACKAGES` |
| `--base-image=IMAGE` | Debian/Ubuntu base image, e.g. `debian:13` |
| `--image-name=NAME` | resulting image name (default `ryad`) |
| `--config=FILE` | another settings file, read after `~/.config/ryad/build.conf` |
| `--context=DIR` | build from the build files in DIR instead of the embedded ones |
| `--export=DIR` | write the build files to DIR, don't build |

## Settings files

All three use shell syntax.

### `~/.config/ryad/build.conf`

Overrides the built-in [build.conf](../build.conf). See [Customization](customization.md).

| Setting | Default | |
|---|---|---|
| `BASE_IMAGE` | `ubuntu:26.04` | Ubuntu ≥ 22.04 or Debian ≥ 12 |
| `IMAGE_NAME` | `ryad` | tagged `:latest` and `:cc-<code>_cd-<desktop>` |
| `APPS` | `firefox vscodium rstudio antigravity pi` | apps from `apps/<name>.sh`: a list, and/or changes to it (`+name`, `-name`). See [Choose the apps](customization.md#choose-the-apps) |
| `EXTRA_PACKAGES` | | apt packages, on top of `packages/*.list` |
| `CLAUDE_CODE_VERSION` | `latest` | `latest`, `stable` or `X.Y.Z` |
| `CLAUDE_DESKTOP_VERSION` | `latest` | `latest` or `X.Y.Z` |
| `RSTUDIO_VERSION` | `latest` | `latest` or e.g. `2026.10.0-233` |
| `ANTIGRAVITY_VERSION` | `latest` | `latest` or `X.Y.Z` |
| `PI_VERSION` | `latest` | `latest` or `X.Y.Z` |
| `<APP>_VERSION` | | passed to `apps/<app>.sh`, e.g. `VSCODIUM_VERSION`. `latest` is looked up at each build for apps with an `@latest` line, otherwise only with `--refresh` |

### `profiles/<name>/profile.conf`

See [Profiles](profiles.md#creation-defaults-and-prompt-colors-profileconf).

| Setting | Applies | |
|---|---|---|
| `IMAGE` | at creation | like `--image` |
| `DISPLAY_MODE` | at creation | like `--display` |
| `GPU` | at creation | `0` is like `--no-gpu` (default `1`) |
| `USER_NAME` | at creation | like `--user` |
| `HOST_NAME` | at creation | like `--hostname` |
| `PROMPT_COLORS` | at each enter | e.g. `"user=bold-green host=yellow dir=1;34"` |

### `profiles/<name>/profile.env`

`KEY=value` lines, passed to every shell and app at each enter. See [Profiles](profiles.md#environment-variables-profileenv).

## Environment variables

Read by the launcher on the host:

| Variable | |
|---|---|
| `RYAD_HOME` | ryad's config folder (default `${XDG_CONFIG_HOME:-~/.config}/ryad`) |
| `RYAD_PROMPT_COLORS` | overrides the profile's `PROMPT_COLORS` for this shell |
| `RYAD_ELECTRON_NO_SANDBOX=1` | start Electron apps with `--no-sandbox` |
| `VISUAL`, `EDITOR` | editor for `ryad profiles edit` and `ryad apps new` |

Set by the launcher inside an environment: `RYAD_NAME`, `RYAD_PROFILE`, `RYAD_WORKSPACE`, `RYAD_USER`.

## Files and locations

| Path | |
|---|---|
| `~/.config/ryad/build.conf` | your build settings |
| `~/.config/ryad/packages/*.list` | your apt package lists |
| `~/.config/ryad/apps/*.sh` | your app installers (`ryad apps new`) |
| `~/.config/ryad/profiles/<name>/` | a profile (mode 0700) |
| `…/profiles/<name>/home/` | the home directory inside its environments |
| `…/home/.cache/ryad/logs/<cmd>.log` | output of commands started with `--detach` |
| `$XDG_RUNTIME_DIR/ryad/` | stable display links, refreshed at each start |
| container `ryad-<name>` | an environment (`podman logs ryad-<name>`) |
| image `ryad:latest` | the default image |
| `/etc/ryad/apps.list` (in the image) | its apps: name, commands, description |
