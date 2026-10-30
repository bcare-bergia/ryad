#!/usr/bin/env bash
# Test an installer made by release.sh, in a throwaway HOME: install, upgrade,
# a damaged copy, uninstall. Doesn't build images or touch environments.
#
#   tests/installer-test.sh ryad-X.Y.Z.run X.Y.Z
set -euo pipefail

run=$(realpath "${1:?usage: $0 INSTALLER VERSION}") version=${2:?usage: $0 INSTALLER VERSION}
t=$(mktemp -d)
trap 'rm -rf "$t"' EXIT
export HOME=$t/home
mkdir -p "$HOME" "$t/fakebin"
# A podman that answers the installer's rootless check, so that the real one
# isn't run (it would set up its storage in this HOME).
printf '#!/bin/sh\necho true\n' > "$t/fakebin/podman"
chmod +x "$t/fakebin/podman"
export PATH=$t/fakebin:$PATH
p=$HOME/.local
fails=0
ok() { echo "    ok: $*"; }
ko() { echo "    FAIL: $*" >&2; fails=$((fails + 1)); }
check() { # DESCRIPTION COMMAND...: passes if the command does
  local d=$1; shift
  if "$@" >/dev/null 2>&1; then ok "$d"; else ko "$d"; fi
}

check "--help" bash "$run" --help
check "--list carries the bundle" bash -c "bash '$run' --list | grep -qx bin/ryad"
check "--extract" bash "$run" --extract="$t/x"
check "extracted license" test -f "$t/x/share/doc/ryad/LICENSE.md"

# Without a terminal and without --yes, it refuses.
if bash "$run" < /dev/null >/dev/null 2>&1; then ko "refuses without --yes"; else ok "refuses without --yes"; fi
check "nothing installed after refusing" test ! -e "$p/bin/ryad"

# Install
bash "$run" --yes > "$t/install.log" 2>&1 || { cat "$t/install.log"; ko "install"; }
check "bin/ryad is executable" test -x "$p/bin/ryad"
check "ryad --version is $version" bash -c "'$p/bin/ryad' --version | grep -q '^ryad $version '"
check "bin/ryad is the bundle" cmp "$p/bin/ryad" "$t/x/bin/ryad"
check "completion for ryad" grep -q '^complete -F _ryad ryad$' "$p/share/bash-completion/completions/ryad"
check "docs" test -f "$p/share/doc/ryad/docs/getting-started.md"
check "manifest" test -s "$p/share/ryad/install.manifest"
check "next step: ryad build" grep -q "Next: ryad build" "$t/install.log"

# Upgrade over an older version, with a file the new one no longer has.
cat > "$p/bin/ryad" <<'EOF'
#!/usr/bin/env bash
echo "ryad 0.0.1 (000000000000, bundled 2026-01-01)"
EOF
touch "$p/share/doc/ryad/old.md"
echo share/doc/ryad/old.md >> "$p/share/ryad/install.manifest"
bash "$run" --yes > "$t/upgrade.log" 2>&1 || { cat "$t/upgrade.log"; ko "upgrade"; }
check "upgrade notices 0.0.1" grep -q "installed: 0.0.1" "$t/upgrade.log"
check "upgrade replaced bin/ryad" cmp "$p/bin/ryad" "$t/x/bin/ryad"
check "upgrade removed a stale file" test ! -e "$p/share/doc/ryad/old.md"
check "next step: recreate --outdated" grep -q "recreate --outdated" "$t/upgrade.log"

# A damaged copy is refused before installing anything.
n=$(( $(wc -l < "$run") - 1 ))
awk -v n="$n" 'NR == n { c = substr($0, 1, 1); $0 = (c == "A" ? "B" : "A") substr($0, 2) } 1' "$run" > "$t/bad.run"
if bash "$t/bad.run" --yes --prefix="$t/bad" >/dev/null 2>&1; then ko "damaged copy refused"; else ok "damaged copy refused"; fi
check "nothing installed from the damaged copy" test ! -e "$t/bad"

# Another prefix
check "install with --prefix" bash "$run" --yes --prefix="$t/opt"
check "  in it" test -x "$t/opt/bin/ryad"

# Uninstall leaves nothing behind, and only removes its own files.
mkdir -p "$p/bin" && touch "$p/bin/other-tool"
check "uninstall" bash "$run" --uninstall --yes
check "uninstall kept other files" test -e "$p/bin/other-tool"
rm "$p/bin/other-tool"; rmdir "$p/bin" 2>/dev/null || true
left=$(find "$p" -mindepth 1 2>/dev/null)
[ -z "$left" ] && ok "nothing left in $p" || ko "left in $p: $left"
if bash "$run" --uninstall --yes >/dev/null 2>&1; then ko "second uninstall refused"; else ok "second uninstall refused"; fi

[ "$fails" = 0 ] || { echo "    $fails test(s) failed" >&2; exit 1; }
echo "    all passed"
