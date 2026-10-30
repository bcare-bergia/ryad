#!/usr/bin/env bash
# Make dist/ryad: the launcher with the build files appended (as a base64
# tar.gz after a marker line), so that this one file can be copied anywhere and
# still run 'ryad build'. Run it again after editing ryad or the build files.
#
#   ./bundle.sh [-o FILE]
#
# The version is $RYAD_VERSION (release.sh sets it), else 'git describe' of
# this checkout, else "dev". The bundle date is $SOURCE_DATE_EPOCH, else today.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
out=dist/ryad
case ${1:-} in
  -o) out=${2:?usage: ./bundle.sh [-o FILE]} ;;
  "") ;;
  *) echo "usage: ./bundle.sh [-o FILE]" >&2; exit 2 ;;
esac
version=${RYAD_VERSION:-$(git describe --tags --always --dirty 2>/dev/null || echo dev)}
version=${version#v}
date=$(date -u ${SOURCE_DATE_EPOCH:+-d "@$SOURCE_DATE_EPOCH"} +%F)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# The list of build files lives in ryad (BUILD_FILES); let it pick them.
./ryad build --context=. --export="$tmp/files" 2>/dev/null
# Reproducible archive: same files, same bytes, same stamp.
tar -C "$tmp/files" --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 -cf - . \
  | gzip -9n > "$tmp/files.tar.gz"

marker=$(sed -n 's/^MARKER=//p' ryad)
stamp=$(cat ryad "$tmp/files.tar.gz" | sha256sum | cut -c1-12)
mkdir -p "$(dirname "$out")"
{
  sed "s/^RYAD_BUNDLE=\"\"/RYAD_BUNDLE=\"$version $stamp $date\"/" ryad
  printf 'exit 0\n%s\n' "$marker"
  base64 -w 76 "$tmp/files.tar.gz"
} > "$out.new"
chmod 0755 "$out.new"
mv "$out.new" "$out"
echo "$out: ryad $version ($stamp, $(wc -c < "$out") bytes)"
[ "$out" != dist/ryad ] || echo "install it with: install -m 0755 dist/ryad ~/.local/bin/ryad"
