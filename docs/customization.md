# Customization

What goes into the ryad image is up to you: extra packages, other apps, pinned versions, another base distribution. This page goes from the simplest change to the most involved.

- [Where your settings live](#where-your-settings-live)
- [Choose the apps](#choose-the-apps)
- [Add apt packages](#add-apt-packages)
- [Add a third-party app](#add-a-third-party-app)
- [Pin versions](#pin-versions)
- [Change the base image](#change-the-base-image)
- [Edit the built-in build files](#edit-the-built-in-build-files)
- [Build your own image on top](#build-your-own-image-on-top)
- [Applying changes](#applying-changes)

Per-profile settings (API keys, prompt colors, default image) are covered in [Profiles](profiles.md).

## Where your settings live

Your own build settings and additions live in `~/.config/ryad/`, next to the profiles. `ryad build` adds them to its built-in files:

```
~/.config/ryad/
├── build.conf          # settings: APPS=, EXTRA_PACKAGES=, BASE_IMAGE=, IMAGE_NAME=, versions
├── packages/*.list     # extra apt package lists
└── apps/*.sh           # your app installers (ryad apps new)
```

Settings apply in this order, later ones winning:

1. the built-in [build.conf](../build.conf)
2. `~/.config/ryad/build.conf`
3. `--config=FILE`
4. command-line options (`ryad build --help`)

A file in `packages/` or `apps/` with the same name as a built-in one replaces it. The built-in files are in [packages/](../packages) and [apps/](../apps).

## Choose the apps

`ryad apps` lists the apps the image can have: which ones the current image has, and the changes waiting for the next build.

```
$ ryad apps
APP             STATUS                 SOURCE    COMMANDS        DESCRIPTION
claude-code     always                 built-in  claude          Claude Code, Anthropic's coding agent (terminal)
claude-desktop  always                 built-in  claude-desktop  Claude Desktop, Anthropic's desktop app
firefox         installed              built-in  firefox         Firefox web browser; opens the other apps' sign-in pages
vscodium        installed              built-in  codium          VSCodium, the open-source build of VS Code
rstudio         removed at next build  built-in  rstudio         RStudio Desktop, IDE for R
antigravity     installed              built-in  antigravity     Google Antigravity, agent-first IDE
pi              installed              built-in  pi              Pi coding agent (terminal)
```

Add or remove apps by name:

```bash
ryad apps rm rstudio antigravity
ryad apps add rstudio
```

The change is saved in `~/.config/ryad/build.conf`. ryad then offers to rebuild the image and recreate the environments on it; to do that later, run `ryad build`, then `ryad recreate --outdated`. Each app has its own image layer, so adding or removing one doesn't reinstall the others.

Claude Code and Claude Desktop are always installed. Emacs comes from [packages/30-editors.list](../packages/30-editors.list); to drop it, replace that list with an empty file of the same name in `~/.config/ryad/packages/`.

Removing an app leaves its settings and logins in the profiles' home folders (`~/.config/VSCodium`, `~/.pi`…), so adding it back later picks them up again.

> [!NOTE]
> Without Firefox, sign-in pages (`pi` and `claude` `/login`, Antigravity, Claude Desktop) can't open in a browser. Terminal tools print a URL instead; desktop apps may not be able to sign in at all. ryad warns when you remove an app that another one needs.

### The `APPS` setting

`ryad apps add` and `rm` edit the `APPS=` line of `~/.config/ryad/build.conf`. You can also write it yourself:

| `APPS=` | |
|---|---|
| `"-rstudio -antigravity"` | changes to the built-in list: `+name` adds an app, `-name` removes one. Apps added to the built-in list by later versions of ryad still get installed |
| `"firefox pi"` | a list that replaces the built-in one |
| `"firefox pi -mytool"` | a list, then changes to it |

The built-in list is `firefox vscodium rstudio antigravity pi`. [Your own apps](#add-a-third-party-app) are installed unless `APPS` removes them with `-name`.

To try a list for one build only: `ryad build --apps="-rstudio"`. The next `ryad build` goes back to your settings; until then, `ryad apps` shows the difference as pending.

## Add apt packages

Put package names in a list, one per line, with `#` for comments:

```bash
mkdir -p ~/.config/ryad/packages
cat >> ~/.config/ryad/packages/50-mine.list <<'EOF'
# Databases
postgresql-client
sqlite3
EOF
ryad build
```

For a one-off build: `ryad build --packages="htop postgresql-client"`. You can also set `EXTRA_PACKAGES="…"` in `~/.config/ryad/build.conf`.

## Add a third-party app

This is how you bring another agent or LLM tool into the image: a CLI from npm or pip, a desktop app, a local model runner. For anything that isn't a plain distro package (it needs its own apt repository, a downloaded `.deb`, a tarball…), write an installer script:

1. Run `ryad apps new <name>`. It writes `~/.config/ryad/apps/<name>.sh` from a template and opens it in your editor. The script runs as root during the image build; see [apps/README](../apps/README) for the contract.
2. Optionally pin its version with `<NAME>_VERSION=…` in `~/.config/ryad/build.conf`, e.g. `FOO_VERSION=1.2.3`.
3. Run `ryad build`, then `ryad recreate --outdated`.

Apps in `~/.config/ryad/apps/` are installed without being added to `APPS`. To leave one out without deleting its script: `ryad apps rm <name>`.

A minimal installer, from an apt repository:

```bash
# @description Foo, a command-line agent
# @commands foo
. "$(dirname "$0")/lib.sh"
curl -fsSL https://example.com/key.asc -o /usr/share/keyrings/foo.asc
echo "deb [signed-by=/usr/share/keyrings/foo.asc] https://example.com/apt stable main" \
  > /etc/apt/sources.list.d/foo.list
apt-get update
v=${FOO_VERSION:-latest}
apt-get install -y --no-install-recommends "foo$([ "$v" = latest ] || echo "=$v")"
apt_clean
```

The `# @` lines at the top describe the app to ryad:

| Line | |
|---|---|
| `# @description TEXT` | one line, shown by `ryad apps` |
| `# @commands CMD…` | the commands it adds, listed by `ryad apps` and in the shell banner |
| `# @needs APP…` | apps it relies on, e.g. `firefox` for sign-in pages. ryad warns when one of them isn't installed |
| `# @latest COMMAND` | prints the app's newest version. `ryad build` runs it before building, so a new release rebuilds the app's layer. Without it, `latest` is only looked up again with `ryad build --refresh` |

`@latest` commands run in a throwaway container of the previous image (which has `curl` and `jq`), with `BASE_ID`, `BASE_VERSION`, `BASE_CODENAME` and `DEB_ARCH` describing the image being built. See [apps/rstudio.sh](../apps/rstudio.sh) for an example.

For a tool distributed on npm, see [apps/pi.sh](../apps/pi.sh): it installs the package system-wide in `/opt`, since the home directory is replaced by the profile at runtime. For an Electron app, `apps/lib.sh` provides `electron_wrapper`, which adds keyring storage and the one-instance-per-profile lock. See how [apps/vscodium.sh](../apps/vscodium.sh) uses it, and [Foundations](foundations.md#electron-app-wrappers) for what it does.

To change a built-in installer, run `ryad apps new` with its name: it copies the built-in script to `~/.config/ryad/apps/`, where yours replaces it.

## Pin versions

By default, `ryad build` takes the latest releases. To pin, set the versions in `~/.config/ryad/build.conf`:

```bash
CLAUDE_CODE_VERSION=stable        # latest | stable | X.Y.Z
CLAUDE_DESKTOP_VERSION=3.6556.1   # latest | X.Y.Z
RSTUDIO_VERSION=2026.10.0-233     # latest | X.Y.Z-N
ANTIGRAVITY_VERSION=2.28.2        # latest | X.Y.Z
PI_VERSION=1.4.0                  # latest | X.Y.Z
VSCODIUM_VERSION=1.105.0.25000    # any <APP>_VERSION is passed to apps/<app>.sh
                                  # ('-' and '.' in the app name become '_')
```

or on the command line:

```bash
ryad build --code-version=stable --desktop-version=3.6556.1
```

`ryad versions` shows what an image contains.

## Change the base image

The default base is `ubuntu:26.04`. Any Debian or Ubuntu image works (Ubuntu ≥ 22.04, Debian ≥ 12). Other distributions don't: some of the apps are only shipped as `.deb` packages.

Build a variant under its own name, so it sits next to the default image:

```bash
ryad build --base-image=debian:13 --image-name=ryad-debian
ryad acme-debian --workspace="$HOME/projects/acme" --image=ryad-debian
```

To keep a variant around, put its settings in a file and build with `--config`:

```bash
# ~/ryad-debian.conf
BASE_IMAGE=debian:13
IMAGE_NAME=ryad-debian
```

```bash
ryad build --config ~/ryad-debian.conf
```

## Edit the built-in build files

To change the Dockerfile, the user setup, the entrypoint…, export the built-in files, edit them, and build from that folder:

```bash
ryad build --export ~/my-ryad
# edit ~/my-ryad/Dockerfile, ~/my-ryad/entrypoint.sh, ...
ryad build --context ~/my-ryad
```

In this repository, edit the files directly and use `./build.sh`, or run `./bundle.sh` to make a `ryad` that carries your changes. [Foundations](foundations.md) explains what each file does.

## Build your own image on top

You can also derive an image from `ryad:latest` with a regular Containerfile. See [examples/Dockerfile.custom](../examples/Dockerfile.custom):

```dockerfile
FROM localhost/ryad:latest
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client graphviz \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm && npm cache clean --force
USER claude
```

```bash
podman build -t my-ryad -f examples/Dockerfile.custom .
ryad acme --image=my-ryad        # a new environment on it
```

To make it the default for a profile, set `IMAGE=my-ryad` in its [`profile.conf`](profiles.md#creation-defaults-and-prompt-colors-profileconf).

> [!WARNING]
> Install tools system-wide, never under `/home`: at runtime the home directory is replaced by the profile.
>
> A derived image doesn't follow `ryad build` by itself. Rebuild it after each `ryad build` to pick up new app versions.

## Applying changes

A new image only affects environments created or recreated after it is built:

```bash
ryad build
ryad recreate --outdated      # or: ryad recreate acme
```

See [Upgrading](upgrading.md) for the full cycle, including cleaning up old images.
