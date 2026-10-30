#!/usr/bin/env bash
# Make dist/ryad: the launcher with the build files appended (as a base64
# tar.gz after a marker line), so that this one file can be copied anywhere and
# still run 'ryad build'. Run it again after editing ryad or the build files.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# The list of build files lives in ryad (BUILD_FILES); let it pick them.
./ryad build --context=. --export="$tmp/files" 2>/dev/null
# Reproducible archive: same files, same bytes, same stamp.
tar -C "$tmp/files" --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 -cf - . \
  | gzip -9n > "$tmp/files.tar.gz"

marker=$(sed -n 's/^MARKER=//p' ryad)
stamp=$(cat ryad "$tmp/files.tar.gz" | sha256sum | cut -c1-12)
mkdir -p dist
{
  sed "s/^RYAD_BUNDLE=\"\"/RYAD_BUNDLE=\"$stamp $(date +%F)\"/" ryad
  printf 'exit 0\n%s\n' "$marker"
  base64 -w 76 "$tmp/files.tar.gz"
} > dist/ryad.new
chmod 0755 dist/ryad.new
mv dist/ryad.new dist/ryad
echo "dist/ryad: ryad $stamp ($(wc -c < dist/ryad) bytes)"
echo "install it with: install -m 0755 dist/ryad ~/.local/bin/ryad"
