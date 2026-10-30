#!/usr/bin/env bash
# ryad @VERSION@ installer, made by release.sh. Run it with: bash ryad.run
# Installs ryad for your user (~/.local by default); see --help.
#
# Copyright (c) 2026 Bertrand Care. Sustainable Use License 1.0, see LICENSE.md
# ('--extract=DIR' writes it out). Provided as is, without warranty or liability.
#
# After the marker line at the end of this file: a base64 tar.gz of
#   bin/ryad
#   share/bash-completion/completions/ryad
#   share/doc/ryad/          README.md, CHANGELOG.md, LICENSE.md, docs/
# installed as is under the prefix.
set -euo pipefail

VERSION=@VERSION@
PAYLOAD_SHA256=@PAYLOAD_SHA256@
MARKER=__RYAD_INSTALLER_PAYLOAD__
SELF=${BASH_SOURCE[0]}
PROG=$(basename "$SELF")
MANIFEST_REL=share/ryad/install.manifest

usage() {
  cat <<EOF
ryad $VERSION installer

  bash $PROG [--prefix=DIR] [--yes]   install, or upgrade an earlier install
  bash $PROG --uninstall [--prefix=DIR] [--yes]
  bash $PROG --list                   list the files it carries
  bash $PROG --extract=DIR            write them to DIR, don't install

  --prefix=DIR   where to install (default: ~/.local): DIR/bin/ryad, plus
                 the shell completion and docs under DIR/share
  --yes, -y      accept the license and don't ask

It never touches your profiles, settings (~/.config/ryad), images or environments.
EOF
}

die() { echo "error: $*" >&2; exit 1; }
note() { echo "$*" >&2; }

prefix=${HOME:?}/.local yes=0 action=install extract=""
for a in "$@"; do
  case $a in
    --prefix=*) prefix=${a#*=} ;;
    --yes|-y) yes=1 ;;
    --uninstall) action=uninstall ;;
    --list) action=list ;;
    --extract=*) action=extract extract=${a#*=} ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown option: $a (see --help)" ;;
  esac
done
[ -n "$prefix" ] || die "--prefix is empty"
prefix=$(realpath -m "$prefix")
manifest=$prefix/$MANIFEST_REL

ask() { # QUESTION: yes or no, "no" by default
  [ "$yes" = 1 ] && return 0
  [ -t 0 ] || die "not a terminal: run again with --yes to $1"
  local r
  read -r -p "$2 [y/N] " r
  [[ $r == [yY]* ]]
}

prune() { # FILE: remove it, then its folders as they become empty, up to the prefix
  local d
  rm -f "$prefix/$1"
  d=$(dirname "$prefix/$1")
  while [ "$d" != "$prefix" ] && [[ $d == "$prefix"/* ]] && rmdir "$d" 2>/dev/null; do
    d=$(dirname "$d")
  done
}

payload() { awk -v m="$MARKER" 'f { print } $0 == m { f = 1 }' "$SELF" | base64 -d; }

unpack() { # DIR: the verified payload, unpacked there
  [ -f "$SELF" ] || die "can't read myself ($SELF): download $PROG first, then run it"
  local sum
  sum=$(payload | sha256sum | cut -d' ' -f1)
  [ "$sum" = "$PAYLOAD_SHA256" ] || die "$PROG is damaged (checksum mismatch): download it again"
  mkdir -p "$1"
  payload | tar -xz -C "$1"
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# --- uninstall ---------------------------------------------------------------------
if [ "$action" = uninstall ]; then
  [ -f "$manifest" ] || die "no ryad installed by this installer in $prefix (no $manifest)"
  ask "uninstall" "Remove ryad from $prefix? Your profiles, settings, images and environments stay." \
    || { note "nothing removed"; exit 1; }
  while IFS= read -r f; do prune "$f"; done < "$manifest"
  prune "$MANIFEST_REL"
  echo "ryad removed from $prefix."
  echo "Left in place: ~/.config/ryad (profiles, settings), and the ryad images and"
  echo "containers (podman rmi / podman rm, or 'ryad rm' and 'ryad prune' before uninstalling)."
  exit 0
fi

unpack "$tmp/p"
files=$(cd "$tmp/p" && find . -type f | sed 's|^\./||' | LC_ALL=C sort)

case $action in
  list) echo "$files"; exit 0 ;;
  extract)
    mkdir -p "$extract"
    cp -a "$tmp/p/." "$extract/"
    echo "ryad $VERSION written to $extract"
    exit 0 ;;
esac

# --- install -------------------------------------------------------------------------
old=""
[ ! -x "$prefix/bin/ryad" ] || old=$("$prefix/bin/ryad" --version 2>/dev/null | awk '{ print $2 }') || true

echo "ryad $VERSION${old:+ (installed: $old)}, into $prefix"
cat <<'EOF'

  ryad is (c) 2026 Bertrand Caré, under the Sustainable Use License 1.0.
  You may use and modify it for yourself or your own business, and share it
  free of charge for non-commercial purposes. You may not sell it, offer it as
  a paid product or service, or remove its license notices.

  It was written mostly with LLM coding agents, has not been audited, and comes
  AS IS, WITHOUT ANY WARRANTY: you use it at your own risk. Its author and
  BERGIA Solutions accept no liability for it. The full text is in LICENSE.md.

EOF
ask "accept the license" "Accept the license and install?" || { note "nothing installed"; exit 1; }

# Requirements: warn only, ryad itself says what it needs when it needs it.
missing=""
for c in podman curl jq; do command -v "$c" >/dev/null || missing+=" $c"; done
[ -z "$missing" ] || note "warning: not installed:$missing (ryad needs podman, and curl and jq for 'ryad build')"
if command -v podman >/dev/null \
   && [ "$(podman info --format '{{.Host.Security.Rootless}}' 2>/dev/null)" != true ]; then
  note "warning: podman doesn't run rootless here; ryad needs rootless podman"
fi

# Copy each file next to its destination, then rename it over: a running ryad
# keeps its old file, and a failure leaves the previous install whole.
while IFS= read -r f; do
  d=$prefix/$f
  mkdir -p "$(dirname "$d")"
  cp "$tmp/p/$f" "$d.new.$$"
  mv -f "$d.new.$$" "$d"
done <<<"$files"
# Files of the previous install that this one doesn't have (renamed docs...).
if [ -f "$manifest" ]; then
  while IFS= read -r f; do
    grep -qxF -- "$f" <<<"$files" || prune "$f"
  done < "$manifest"
fi
mkdir -p "$(dirname "$manifest")"
echo "$files" > "$manifest"

echo "Installed: $prefix/bin/ryad ($("$prefix/bin/ryad" --version))"

# What changed since the installed version, from the changelog: the sections
# down to that version, or only this one when the installed one has no
# version number (a bundle from before releases).
if [ -n "$old" ] && [ "$old" != "$VERSION" ]; then
  since=$old
  [[ $since =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || since=""
  echo
  echo "Changes${since:+ since $since}:"
  awk -v old="$since" -v new="$VERSION" '
    /^## \[/ { v = $2; gsub(/[][]/, "", v)
               if (v == old || (old == "" && seen)) exit
               show = (v != "Unreleased"); if (v == new) seen = 1 }
    show' "$tmp/p/share/doc/ryad/CHANGELOG.md" | sed 's/^/  /'
fi

case ":$PATH:" in
  *":$prefix/bin:"*) ;;
  *) note "warning: $prefix/bin is not on your PATH; add it, e.g. in ~/.profile: PATH=\"$prefix/bin:\$PATH\"" ;;
esac
w=$(command -v ryad || true)
[ -z "$w" ] || [ "$(realpath "$w")" = "$prefix/bin/ryad" ] \
  || note "warning: 'ryad' runs $w, which comes first on your PATH"

echo
if [ -n "$old" ]; then
  echo "Next, to move your environments onto the new version: ryad build && ryad recreate --outdated"
else
  echo "Next: ryad build (a few GB, the first time), then 'ryad' in a project folder."
  echo "Shell completion works in new shells; the docs are in $prefix/share/doc/ryad."
fi
exit 0
