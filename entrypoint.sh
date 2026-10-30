#!/bin/bash
# Container init for ryad (runs as UID 1000 under `podman --init`).
#  - names the user as chosen at creation
#  - prepares $XDG_RUNTIME_DIR and the profile home
#  - starts a private session D-Bus and an unlocked gnome-keyring (Secret Service),
#    so Claude Desktop can persist its sign-in inside the profile
#  - then idles until the environment is stopped (`ryad stop`);
#    terminals and apps are started with `podman exec`
set -u

# User name chosen at creation (ryad --user=): rename the image's
# user once; the container filesystem keeps it across restarts.
if [ -n "${RYAD_USER:-}" ] && [ "$(id -un)" != "$RYAD_USER" ]; then
  sudo -n /usr/local/sbin/ryad-setuser "$RYAD_USER" || exit 1
fi

mkdir -p "$XDG_RUNTIME_DIR" && chmod 0700 "$XDG_RUNTIME_DIR"

# First run of a profile: seed the (empty) home from /etc/skel.
if [ ! -e "$HOME/.bashrc" ]; then
  cp -rn /etc/skel/. "$HOME/" 2>/dev/null || true
fi
mkdir -p "$HOME/.local/share/keyrings" "$HOME/.config"

# Private session bus at a fixed address (see DBUS_SESSION_BUS_ADDRESS in the image).
rm -f "${DBUS_SESSION_BUS_ADDRESS#unix:path=}" "$XDG_RUNTIME_DIR/ready"
dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --nopidfile --fork
for _ in $(seq 50); do [ -S "${DBUS_SESSION_BUS_ADDRESS#unix:path=}" ] && break; sleep 0.1; done

# Keyring: the default "login" keyring lives in the profile and is stored
# unencrypted (gnome-keyring's plain-text format), so it never needs unlocking
# and never pops up a password prompt. The profile directory (mode 0700 on the
# host) is the trust boundary.
KR=$HOME/.local/share/keyrings
if [ ! -e "$KR/login.keyring" ]; then
  printf '[keyring]\ndisplay-name=Login\nctime=0\nmtime=0\nlock-on-idle=false\nlock-after=false\n' > "$KR/login.keyring"
  chmod 0600 "$KR/login.keyring"
fi
[ -s "$KR/default" ] || printf 'login' > "$KR/default"
gnome-keyring-daemon --daemonize --start --components=secrets >/dev/null 2>&1

touch "$XDG_RUNTIME_DIR/ready"

if [ "${1:-idle}" != idle ]; then
  exec "$@"
fi

# Keep the environment alive until it is stopped. PID 1 (podman --init)
# forwards SIGTERM, so `podman stop` is immediate.
exec sleep infinity
