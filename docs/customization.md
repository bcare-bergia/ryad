# Customization

What goes into the ryad image is up to you: extra packages, other apps, pinned versions, another base distribution. This page goes from the simplest change to the most involved.

- [Where your settings live](#where-your-settings-live)
- [Add apt packages](#add-apt-packages)
- [Add a third-party app](#add-a-third-party-app)
- [Remove an app](#remove-an-app)
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
└── apps/*.sh           # extra app installers
```

Settings apply in this order, later ones winning:

1. the built-in [build.conf](../build.conf)
2. `~/.config/ryad/build.conf`
3. `--config=FILE`
4. command-line options (`ryad build --help`)

A file in `packages/` or `apps/` with the same name as a built-in one replaces it. The built-in files are in [packages/](../packages) and [apps/](../apps).

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

For an app that isn't a plain distro package (it needs its own apt repository, a downloaded `.deb`, a tarball…), write an installer script:

1. Write `~/.config/ryad/apps/<name>.sh`. It runs as root during the image build. See [apps/README](../apps/README) for the contract and an example. Apps in this folder are installed without listing them in `APPS`.
2. Optionally pin its version with `<NAME>_VERSION=…` in `~/.config/ryad/build.conf`, e.g. `FOO_VERSION=1.2.3`.
3. Run `ryad build`.

A minimal installer, from an apt repository:

```bash
. "$(dirname "$0")/lib.sh"
curl -fsSL https://example.com/key.asc -o /usr/share/keyrings/foo.asc
echo "deb [signed-by=/usr/share/keyrings/foo.asc] https://example.com/apt stable main" \
  > /etc/apt/sources.list.d/foo.list
apt-get update
v=${FOO_VERSION:-latest}
apt-get install -y --no-install-recommends "foo$([ "$v" = latest ] || echo "=$v")"
apt_clean
```

For an Electron app, `apps/lib.sh` provides `electron_wrapper`, which adds keyring storage and the one-instance-per-profile lock. See how [apps/vscodium.sh](../apps/vscodium.sh) uses it, and [Foundations](foundations.md#electron-app-wrappers) for what it does.

## Remove an app

Set `APPS` in `~/.config/ryad/build.conf` without it. The built-in list is:

```bash
APPS="firefox vscodium rstudio"
```

Claude Code and Claude Desktop are always installed. Emacs comes from [packages/30-editors.list](../packages/30-editors.list); to drop it, replace that list with an empty file of the same name in `~/.config/ryad/packages/`.

> [!NOTE]
> Without Firefox, `claude /login` prints a URL instead of opening a browser, and Claude Desktop's sign-in may not work.

## Pin versions

By default, `ryad build` takes the latest releases. To pin, set the versions in `~/.config/ryad/build.conf`:

```bash
CLAUDE_CODE_VERSION=stable        # latest | stable | X.Y.Z
CLAUDE_DESKTOP_VERSION=3.6556.1   # latest | X.Y.Z
RSTUDIO_VERSION=2026.10.0-233     # latest | X.Y.Z-N
VSCODIUM_VERSION=1.105.0.25000    # any <APP>_VERSION is passed to apps/<app>.sh
```

or on the command line:

```bash
ryad build --code-version=stable --desktop-version=3.6556.1
```

`ryad versions` shows what an image contains.

## Change the base image

The default base is `ubuntu:26.04`. Any Debian or Ubuntu image works (Ubuntu ≥ 22.04, Debian ≥ 12), because Claude Desktop is only shipped as a `.deb`.

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
> A derived image doesn't follow `ryad build` by itself. Rebuild it after each `ryad build` to pick up new Claude versions.

## Applying changes

A new image only affects environments created or recreated after it is built:

```bash
ryad build
ryad recreate --outdated      # or: ryad recreate acme
```

See [Upgrading](upgrading.md) for the full cycle, including cleaning up old images.
