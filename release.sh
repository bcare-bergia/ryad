#!/usr/bin/env bash
# release.sh: make the release files of ryad from the vX.Y.Z tag on the
# current commit, and optionally upload them as a draft GitHub release.
#
# USAGE
#   ./release.sh --snapshot                  try a release of the working tree
#   ./release.sh --key=FILE                  build, test and sign vX.Y.Z locally
#   ./release.sh --key=FILE --publish        the same, then upload it as a draft
#
#   --snapshot   build from the working tree (tracked and untracked files, not
#                ignored ones), unsigned, into dist/release/snapshot/. For
#                trying the installer before tagging; never published.
#   --key=FILE   SSH private key to sign SHA256SUMS with (FILE.pub must be
#                next to it). Default: $RYAD_SIGNING_KEY. Users check the
#                signature against github.com/bcare-bergia.keys, so use a key
#                listed there.
#   --publish    after building, ask, then upload the files with gh as a DRAFT
#                release vX.Y.Z. Nothing is public until you publish the draft.
#   --help       this text
#
# The version is not an argument: it comes from git. The current commit (HEAD)
# must carry exactly one tag of the form vX.Y.Z.
#
# PREPARING A RELEASE
#   1. Pick the version (semantic versioning): X for incompatible changes (to
#      profiles, settings, commands), Y for new features, Z for fixes only.
#   2. CHANGELOG.md: rename "## [Unreleased]" to "## [X.Y.Z] - YYYY-MM-DD", add
#      a new, empty "## [Unreleased]" above it, and check the section says
#      what users need to know, upgrade steps included. Commit.
#   3. Try it: ./release.sh --snapshot, then install the snapshot installer on
#      a real machine (see CHECKS below).
#   4. Tag it, but don't push yet: git tag -a vX.Y.Z -m "ryad X.Y.Z"
#   5. ./release.sh --key=FILE. If it fails, fix, commit, and move the tag:
#      git tag -d vX.Y.Z, then tag again. Easy while the tag isn't pushed.
#   6. git push origin main vX.Y.Z
#   7. ./release.sh --key=FILE --publish. It rebuilds the same bytes and uploads
#      them as a draft.
#   8. Review the draft on GitHub (notes, the four files), then publish it there,
#      or: gh release edit vX.Y.Z --draft=false
#   Once published, a version is final: never move or reuse its tag. To fix
#   it, release X.Y.(Z+1).
#
# CHECKS
#   Done by this script, which stops at the first failure:
#   - HEAD has exactly one vX.Y.Z tag; the signing key and its .pub exist
#   - ryad, bundle.sh and installer/stub.sh parse (bash -n), and pass
#     shellcheck when it is installed
#   - CHANGELOG.md has a non-empty "## [X.Y.Z]" section
#   - LICENSE.md, README.md and docs/ are in the tag (they go in the installer)
#   - two builds come out byte for byte the same (reproducible)
#   - tests/installer-test.sh passes: install, upgrade, damaged copy, other
#     prefix, uninstall, in a throwaway HOME (it doesn't build images)
#   - the signature verifies with the public key
#   - with --publish: the tag is on origin, and gh is installed
#
#   To do yourself, on the snapshot or the release candidate, since the script
#   can't build images or run apps:
#   - install it over the previous release: the upgrade notes are right, and
#     'ryad --version' shows X.Y.Z
#   - ryad build, then ryad recreate --outdated on an existing environment:
#     it starts, the apps launch, logins and workspace are still there
#   - a new environment in a new profile, from scratch
#   - the docs match what changed (README, docs/, ryad --help)
#   - nothing private in the tag: git archive vX.Y.Z | tar -t
#   - with --publish: gh auth status
#
# OUTPUT, in dist/release/X.Y.Z/
#   ryad-X.Y.Z          the single-file bundle (as bundle.sh makes it)
#   ryad-X.Y.Z.run      the installer: installer/stub.sh with the bundle, shell
#                       completion and docs appended as a base64 tar.gz
#   SHA256SUMS          checksums of both
#   SHA256SUMS.sig      its SSH signature (ssh-keygen -Y sign, namespace "file")
#   RELEASE_NOTES.md    the version's section of CHANGELOG.md
#
# The files are built from the tag (git archive), never from the working tree,
# with dates taken from the tagged commit; uncommitted changes can't leak in.
# See also: docs/foundations.md#releases.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
die() { echo "error: $*" >&2; exit 1; }
step() { echo "==> $*"; }

key=${RYAD_SIGNING_KEY:-} publish=0 snapshot=0
for a in "$@"; do
  case $a in
    --snapshot) snapshot=1 ;;
    --key=*) key=${a#*=} ;;
    --publish) publish=1 ;;
    --help|-h) sed -n '2,/^set -e/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $a (see --help); the version comes from the tag on HEAD" ;;
  esac
done
if [ "$snapshot" = 1 ]; then
  [ "$publish" = 0 ] || die "a snapshot can't be published"
  version=$(git describe --tags --always --dirty 2>/dev/null || echo dev)
  version=${version#v} out=dist/release/snapshot
else
  # The release tag on HEAD: vX.Y.Z, exactly one.
  tags=$(git tag --points-at HEAD | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true)
  case $(grep -c . <<<"$tags") in
    1) tag=$tags ;;
    0) last=$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null || true)
       die "HEAD ($(git rev-parse --short HEAD)) has no vX.Y.Z tag${last:+ (the last one is $last)}: update CHANGELOG.md, commit, then: git tag -a vX.Y.Z -m 'ryad X.Y.Z'" ;;
    *) die "HEAD has several release tags: $(echo $tags)" ;;
  esac
  version=${tag#v} out=dist/release/${tag#v}
  [ -n "$key" ] || die "no signing key: --key=FILE or RYAD_SIGNING_KEY=FILE (an SSH private key)"
  [ -f "$key" ] && [ -f "$key.pub" ] || die "$key or $key.pub not found"
fi
for c in git tar gzip base64 sha256sum ssh-keygen; do command -v "$c" >/dev/null || die "$c is needed"; done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# --- sources -------------------------------------------------------------------------
src=$tmp/src
mkdir -p "$src"
if [ "$snapshot" = 1 ]; then
  step "Sources: working tree (tracked and untracked, not ignored)"
  git ls-files -coz --exclude-standard | tar --null -T - -cf - | tar -xf - -C "$src"
  epoch=$(date +%s)
else
  step "Sources: $tag ($(git rev-parse --short "$tag^{commit}"))"
  git archive "$tag" | tar -xf - -C "$src"
  epoch=$(git log -1 --format=%ct "$tag^{commit}")
fi
export SOURCE_DATE_EPOCH=$epoch RYAD_VERSION=$version

# --- checks --------------------------------------------------------------------------
step "Checks"
for f in ryad bundle.sh installer/stub.sh tests/installer-test.sh LICENSE.md README.md CHANGELOG.md docs; do
  [ -e "$src/$f" ] || die "$f is missing from the sources${tag:+ (not committed before tagging $tag?)}"
done
for f in ryad bundle.sh installer/stub.sh; do bash -n "$src/$f"; done
if command -v shellcheck >/dev/null; then
  shellcheck -S warning "$src/ryad" "$src/bundle.sh" "$src/installer/stub.sh"
else
  echo "    (shellcheck not installed: skipped)"
fi
# The version's changelog section, or for a snapshot, "Unreleased".
section=$([ "$snapshot" = 1 ] && echo Unreleased || echo "$version")
notes=$(awk -v v="$section" '
  /^## \[/ { if (show) exit; s = $2; gsub(/[][]/, "", s); show = (s == v); next }
  show' "$src/CHANGELOG.md" | sed -e '/./,$!d' | sed -e ':a' -e '/^\n*$/{$d;N;ba' -e '}')
[ -n "$notes" ] || [ "$snapshot" = 1 ] || die "CHANGELOG.md has no '## [$version]' section, or it's empty (in $tag)"

# --- build (twice, to check it's reproducible) ----------------------------------------
# build DIR: the bundle, installer and notes, into DIR.
build() {
  local d=$1 p=$tmp/payload.$RANDOM sum f
  mkdir -p "$d"
  (cd "$src" && ./bundle.sh -o "$d/ryad-$version" >/dev/null)
  mkdir -p "$p/bin" "$p/share/bash-completion/completions" "$p/share/doc/ryad"
  cp "$d/ryad-$version" "$p/bin/ryad"
  # Run as 'ryad' (its name), so the completion is registered for 'ryad'.
  "$p/bin/ryad" completion bash > "$p/share/bash-completion/completions/ryad"
  for f in README.md CHANGELOG.md LICENSE.md docs; do cp -r "$src/$f" "$p/share/doc/ryad/"; done
  find "$p" -type d -exec chmod 0755 {} +
  find "$p" -type f -exec chmod 0644 {} +
  chmod 0755 "$p/bin/ryad"
  tar -C "$p" --sort=name --owner=0 --group=0 --numeric-owner --mtime="@$epoch" -cf - . \
    | gzip -9n > "$p.tar.gz"
  sum=$(sha256sum < "$p.tar.gz" | cut -d' ' -f1)
  {
    sed -e "s/@VERSION@/$version/g" -e "s/@PAYLOAD_SHA256@/$sum/" "$src/installer/stub.sh"
    echo __RYAD_INSTALLER_PAYLOAD__
    base64 -w 76 "$p.tar.gz"
  } > "$d/ryad-$version.run"
  chmod 0755 "$d/ryad-$version.run"
  printf '%s\n' "$notes" > "$d/RELEASE_NOTES.md"
}
step "Build"
build "$tmp/a"
build "$tmp/b"
diff -r "$tmp/a" "$tmp/b" >/dev/null || die "two builds differ: the release isn't reproducible"

# --- test ------------------------------------------------------------------------------
step "Test the installer"
"$src/tests/installer-test.sh" "$tmp/a/ryad-$version.run" "$version"

# --- checksums, signature ---------------------------------------------------------------
rm -rf "$out"
mkdir -p "$out"
cp -a "$tmp/a/." "$out/"
(cd "$out" && sha256sum "ryad-$version" "ryad-$version.run" > SHA256SUMS)
if [ "$snapshot" = 0 ]; then
  step "Sign SHA256SUMS with $key"
  ssh-keygen -Y sign -q -f "$key" -n file "$out/SHA256SUMS"
  # Check the signature as a user would, with the public key.
  printf 'ryad %s\n' "$(cat "$key.pub")" > "$tmp/allowed_signers"
  ssh-keygen -Y verify -f "$tmp/allowed_signers" -I ryad -n file -s "$out/SHA256SUMS.sig" \
    < "$out/SHA256SUMS" >/dev/null || die "the signature doesn't verify"
fi

step "Done: $out"
ls -l "$out" | tail -n +2 | sed 's/^/    /'

# --- publish -----------------------------------------------------------------------------
[ "$publish" = 1 ] || exit 0
command -v gh >/dev/null || die "gh is needed to publish"
git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null \
  || die "$tag isn't on origin yet: git push origin $tag"
read -r -p "Upload ryad $version to GitHub as a draft release? [y/N] " r
[[ $r == [yY]* ]] || { echo "not uploaded; the files are in $out"; exit 0; }
step "Draft release $tag"
gh release create "$tag" --draft --verify-tag --title "ryad $version" --notes-file "$out/RELEASE_NOTES.md" \
  "$out/ryad-$version" "$out/ryad-$version.run" "$out/SHA256SUMS" "$out/SHA256SUMS.sig"
echo "    Review it on GitHub, then publish it there, or with: gh release edit $tag --draft=false"
