# Shared helpers for apps/*.sh. Sourced, not executed.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

. /etc/os-release
ARCH=$(dpkg --print-architecture)   # amd64 | arm64
CODENAME=${VERSION_CODENAME:-}

log() { printf '==> [%s] %s\n' "$(basename "$0" .sh)" "$*"; }
die() { printf 'ERROR [%s]: %s\n' "$(basename "$0" .sh)" "$*" >&2; exit 1; }

apt_clean() { apt-get clean; rm -rf /var/lib/apt/lists/*; }

# Register a mime/scheme handler system-wide (/etc/xdg/mimeapps.list).
set_default_handler() { # <desktop-file> <mime>...
  local desktop=$1; shift
  local f=/etc/xdg/mimeapps.list
  [ -f "$f" ] || printf '[Default Applications]\n' > "$f"
  local m
  for m in "$@"; do
    sed -i "\|^$m=|d" "$f"
    printf '%s=%s\n' "$m" "$desktop" >> "$f"
  done
}

# Install /usr/local/bin/<name>, a wrapper around an Electron app that
#  - stores secrets in the Secret Service keyring (there is no desktop
#    environment in the container, so Chromium would fall back to plain text);
#  - adds --no-sandbox when RYAD_ELECTRON_NO_SANDBOX=1;
#  - allows one running instance per profile: several environments can share a
#    profile home, and two instances on the same settings folder corrupt it.
#    The wrapper holds a lock (flock on a file in the shared home, visible
#    across containers) in the foreground until the app's main process is gone,
#    even if the app's launcher returned earlier (codium). A second launch in
#    the *same* environment is let through, so the app's own single-instance
#    handling forwards it (e.g. claude:// sign-in links).
# /usr/local/bin comes first in PATH, so .desktop files and deep links
# (Exec=<name> %U) go through the wrapper too.
electron_wrapper() { # <name> <launcher> <main-process-binary>
  sed -e "s|@NAME@|$1|g" -e "s|@BIN@|$2|g" -e "s|@MAIN@|$3|g" > "/usr/local/bin/$1" <<'WRAP'
#!/bin/bash
set -- --password-store=gnome-libsecret "$@"
[ "${RYAD_ELECTRON_NO_SANDBOX:-0}" = 1 ] && set -- --no-sandbox "$@"

me=${RYAD_NAME:-$(hostname)}
lock=$HOME/.cache/ryad/@NAME@.lock
mkdir -p "${lock%/*}"
exec 9<>"$lock"
if ! flock -n 9; then
  holder=$(head -n1 "$lock" 2>/dev/null)
  if [ "$holder" != "$me" ]; then
    echo "@NAME@ is already running in environment '$holder', which uses the same profile." >&2
    echo "Only one instance per profile can run at a time: close it there, or use another profile." >&2
    exit 1
  fi
  exec 9>&- @BIN@ "$@"   # same environment: the running instance takes over
fi
printf '%s\n' "$me" > "$lock"

main_running() {
  ps -u "$(id -u)" -o args= | awk -v m="@MAIN@" 'index($0, m) == 1 && $0 !~ /--type=/ { f = 1 } END { exit !f }'
}
@BIN@ "$@" 9>&-
rc=$?
while main_running; do sleep 2; done
exit $rc
WRAP
  chmod 0755 "/usr/local/bin/$1"
}
