# Upgrading

Apps don't update themselves inside the sandbox: they are installed system-wide, out of reach of their own updaters, and self-updates are turned off where possible. Upgrades go through the image instead: rebuild it, then move your environments onto it. That keeps every environment on a known, identical set of versions.

- [The upgrade cycle](#the-upgrade-cycle)
- [Security updates](#security-updates)
- [Cleaning up old images](#cleaning-up-old-images)
- [Upgrading ryad itself](#upgrading-ryad-itself)

## The upgrade cycle

```bash
ryad build --check            # latest versions, and whether the image's Claude apps are current
ryad build                    # rebuild; only layers whose version changed are rebuilt
ryad list                     # environments on an older build are marked with *
ryad recreate --outdated      # move them onto the new image (one confirmation for all)
ryad prune                    # remove the old images no container uses
```

Recreating a single environment works too: `ryad recreate acme`.

Recreating keeps the profile and the workspace, so you keep your logins, settings and history. It discards the container's own filesystem, though: anything installed with `sudo apt install` inside the environment is gone. To keep a tool, [add it to the image](customization.md).

To stay on a given version instead, [pin it](customization.md#pin-versions).

## Security updates

`ryad build` reuses the cached layer of distro packages as long as the package lists don't change. To pull the latest security updates from the distribution:

```bash
ryad build --refresh
ryad recreate --outdated
```

It also picks up new releases of the apps whose `latest` version isn't looked up at each build: those whose installer has no `# @latest` line, such as VSCodium and Firefox.

`--no-cache` rebuilds every layer from scratch.

## Cleaning up old images

Each build adds an image of several GB. `ryad prune` lists the ryad images that no container uses, except `:latest` tags, and removes them after you confirm.

## Upgrading ryad itself

Run the installer of the new [release](https://github.com/bcare-bergia/ryad/releases), after checking it as in [Getting started](getting-started.md#from-a-release):

```bash
bash ryad-installer.run
```

It replaces the installed `ryad` and shows what changed since your version, from [CHANGELOG.md](../CHANGELOG.md). Then move your environments onto the new version with `ryad build` and `ryad recreate --outdated`.

From a checkout, update it, then make and install a new bundle:

```bash
./bundle.sh
install -D -m 0755 dist/ryad ~/.local/bin/ryad
ryad --version
```

`ryad versions` shows which bundle built an image, so you can tell whether an image predates your current `ryad`.
