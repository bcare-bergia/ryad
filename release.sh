#!/usr/bin/env bash
# release.sh: make the release files of ryad from the current commit, tag it
# vX.Y.Z once every check passed, and optionally upload them as a draft GitHub
# release.
#
# USAGE
#   ./release.sh --snapshot                    try a release of the working tree
#   ./release.sh --key=FILE --version=X.Y.Z    build, test and sign HEAD, then tag it
#   ./release.sh --key=FILE --publish          rebuild the tagged HEAD, upload a draft
#   Add --pre-check to either of the last two to run all the checks and release
#   nothing.
#
#   --snapshot   build from the working tree (tracked and untracked files, not
#                ignored ones), unsigned, into dist/release/snapshot/. For
#                trying the installer before releasing; never published.
#   --key=FILE   SSH private key to sign SHA256SUMS with (FILE.pub must be
#                next to it). Default: $RYAD_SIGNING_KEY. Users check the
#                signature against github.com/bcare-bergia.keys, so use a key
#                listed there.
#   --version=X.Y.Z
#                the version to release. HEAD is built (committed files only:
#                tracked files must have no uncommitted changes), and tagged
#                vX.Y.Z, an annotated local tag, only once every check passed.
#                Run again on a HEAD already tagged vX.Y.Z, it rebuilds without
#                tagging again.
#   --publish    rebuild the release from the vX.Y.Z tag on HEAD, which must be
#                on origin, ask, then upload the files with gh as a DRAFT
#                release vX.Y.Z. Nothing is public until you publish the draft.
#                With --version, it must match the tag.
#   --pre-check  run every check of the release below (build, test, sign and
#                verify included), in a temporary directory, then stop: nothing
#                is written to dist/, tagged nor uploaded. With --publish, also
#                run its checks; with --snapshot, check the working tree.
#   --help       this text
#
# PREPARING A RELEASE
#   1. Pick the version (semantic versioning): X for incompatible changes (to
#      profiles, settings, commands), Y for new features, Z for fixes only.
#   2. CHANGELOG.md: rename "## [Unreleased]" to "## [X.Y.Z] - YYYY-MM-DD", add
#      a new, empty "## [Unreleased]" above it, and check the section says
#      what users need to know, upgrade steps included. Commit.
#   3. Try it: ./release.sh --snapshot, then install the snapshot installer on
#      a real machine (see CHECKS below).
#   4. ./release.sh --key=FILE --version=X.Y.Z. It tags HEAD vX.Y.Z only if
#      everything passed; if it fails, nothing is tagged: fix, commit, run it
#      again. To change something after it tagged, while the tag isn't pushed:
#      git tag -d vX.Y.Z, fix, commit, run it again.
#   5. git push origin main vX.Y.Z
#   6. ./release.sh --key=FILE --publish. It rebuilds the same bytes from the
#      tag and uploads them as a draft.
#   7. Review the draft on GitHub (notes, the four files), then publish it there,
#      or: gh release edit vX.Y.Z --draft=false
#   Once published, a version is final: never move or reuse its tag. To fix
#   it, release X.Y.(Z+1).
#
# CHECKS
#   Done by this script, which stops at the first failure:
#   - with --version: X.Y.Z is a version, higher than the last vX.Y.Z tag;
#     tracked files have no uncommitted changes; vX.Y.Z doesn't tag another
#     commit, and HEAD has no other vX.Y.Z tag
#   - with --publish: HEAD has exactly one vX.Y.Z tag (the --version, if given)
#   - the signing key and its .pub exist
#   - every script that ships parses (bash -n), and passes shellcheck when
#     it is installed (keep "shellcheck" off the start of a comment line:
#     there it parses as a directive and silently disables the whole file)
#   - CHANGELOG.md has a dated, non-empty "## [X.Y.Z] - YYYY-MM-DD" section
#   - LICENSE.md, README.md and docs/ are committed (they go in the installer)
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
#   - nothing private in the release: git archive HEAD | tar -t
#   - with --publish: gh auth status
#
# OUTPUT, in dist/release/X.Y.Z/
#   ryad                the single-file bundle (as bundle.sh makes it)
#   ryad-installer.run  the installer: installer/stub.sh with the bundle, shell
#                       completion and docs appended as a base64 tar.gz
#   SHA256SUMS          checksums of both
#   SHA256SUMS.sig      its SSH signature (ssh-keygen -Y sign, namespace "file")
#   RELEASE_NOTES.md    the version's section of CHANGELOG.md
#
# The names carry no version: the directory does, and GitHub then serves the
# latest release's files at releases/latest/download/ryad-installer.run, a stable URL.
#
# The files are built from the commit (git archive), never from the working
# tree, with dates taken from that commit; uncommitted changes can't leak in.
# The tag doesn't change the bytes (RYAD_VERSION is set), so --publish, which
# rebuilds from the tag, uploads exactly what --version built and tested.
# See also: docs/foundations.md#releases.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
die() { echo "error: $*" >&2; exit 1; }
step() { echo "==> $*"; }

key=${RYAD_SIGNING_KEY:-} publish=0 snapshot=0 precheck=0 version='' tag='' already_tagged=0
for a in "$@"; do
  case $a in
    --snapshot) snapshot=1 ;;
    --key=*) key=${a#*=} ;;
    --publish) publish=1 ;;
    --version=*) version=${a#*=} version=${version#v} ;;
    --pre-check) precheck=1 ;;
    --help|-h) sed -n '2,/^set -e/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $a (see --help)" ;;
  esac
done
if [ "$snapshot" = 1 ]; then
  [ "$publish" = 0 ] || die "a snapshot can't be published"
  [ -z "$version" ] || die "a snapshot takes its version from git describe, not --version"
  version=$(git describe --tags --always --dirty 2>/dev/null || echo dev)
  version=${version#v} out=dist/release/snapshot
else
  # The release tags (vX.Y.Z) on HEAD.
  tags=$(git tag --points-at HEAD | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true)
  if [ "$publish" = 1 ]; then
    # Publish what --version built and tagged: exactly one tag on HEAD.
    case $(grep -c . <<<"$tags") in
      1) tag=$tags ;;
      0) die "HEAD ($(git rev-parse --short HEAD)) has no vX.Y.Z tag: make the release first: ./release.sh --key=FILE --version=X.Y.Z" ;;
      *) die "HEAD has several release tags: $(echo $tags)" ;;
    esac
    [ -z "$version" ] || [ "v$version" = "$tag" ] || die "--version=$version, but HEAD is tagged $tag"
    version=${tag#v} ref=$tag
  else
    [ -n "$version" ] || die "which version? --version=X.Y.Z (or --snapshot to try the working tree)"
    [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "--version=$version: expected X.Y.Z"
    tag=v$version
    git diff --quiet HEAD -- || die "tracked files have uncommitted changes: commit them first, the release is built from HEAD"
    ref=$(git rev-parse HEAD)
    if old=$(git rev-parse -q --verify "refs/tags/$tag^{commit}"); then
      [ "$old" = "$ref" ] || die "$tag already tags $(git rev-parse --short "$old"); if it isn't pushed, remove it: git tag -d $tag"
      already_tagged=1
    fi
    others=$(grep -vxF "$tag" <<<"$tags" || true)
    [ -z "$others" ] || die "HEAD is already tagged $(echo $others)"
    last=$(git tag -l 'v[0-9]*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | grep -vxF "$tag" | sort -V | tail -n 1 || true)
    [ -z "$last" ] || [ "$(printf '%s\n' "$last" "$tag" | sort -V | tail -n 1)" = "$tag" ] \
      || die "$tag isn't higher than the last release, $last"
  fi
  out=dist/release/$version
  [ -n "$key" ] || die "no signing key: --key=FILE or RYAD_SIGNING_KEY=FILE (an SSH private key)"
  [ -f "$key" ] && [ -f "$key.pub" ] || die "$key or $key.pub not found"
fi
for c in git tar gzip base64 sha256sum ssh-keygen; do command -v "$c" >/dev/null || die "$c is needed"; done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# A pre-check does everything in $tmp, and leaves dist/ alone.
[ "$precheck" = 0 ] || out=$tmp/out

# --- sources -------------------------------------------------------------------------
src=$tmp/src
mkdir -p "$src"
if [ "$snapshot" = 1 ]; then
  step "Sources: working tree (tracked and untracked, not ignored)"
  git ls-files -coz --exclude-standard | tar --null -T - -cf - | tar -xf - -C "$src"
  epoch=$(date +%s)
else
  step "Sources: $tag, commit $(git rev-parse --short "$ref^{commit}")"
  git archive "$ref" | tar -xf - -C "$src"
  epoch=$(git log -1 --format=%ct "$ref^{commit}")
fi
export SOURCE_DATE_EPOCH=$epoch RYAD_VERSION=$version

# --- checks --------------------------------------------------------------------------
step "Checks"
for f in ryad bundle.sh installer/stub.sh tests/installer-test.sh LICENSE.md README.md CHANGELOG.md docs; do
  [ -e "$src/$f" ] || die "$f is missing from the sources${tag:+ (not committed?)}"
done
# Every script that ships: the launcher, the setuser helper, and every *.sh
# (top level, apps/, profile.d/, installer/, tests/). The ones with no shebang
# carry a "shell=bash" directive, so shellcheck knows what it is reading.
scripts=(ryad sbin/ryad-setuser)
while IFS= read -r f; do scripts+=("$f"); done \
  < <(cd "$src" && find . -name '*.sh' -type f | sed 's|^\./||' | sort)
for f in "${scripts[@]}"; do bash -n "$src/$f"; done
if command -v shellcheck >/dev/null; then
  (cd "$src" && shellcheck -S warning "${scripts[@]}")
else
  echo "    (shellcheck not installed: skipped)"
fi
# The version's changelog section, or for a snapshot, "Unreleased".
section=$([ "$snapshot" = 1 ] && echo Unreleased || echo "$version")
notes=$(awk -v v="$section" '
  /^## \[/ { if (show) exit; s = $2; gsub(/[][]/, "", s); show = (s == v); next }
  show' "$src/CHANGELOG.md" | sed -e '/./,$!d' | sed -e ':a' -e '/^\n*$/{$d;N;ba' -e '}')
[ -n "$notes" ] || [ "$snapshot" = 1 ] || die "CHANGELOG.md has no '## [$version]' section, or it's empty (in the commit)"
# A real release is dated: "## [X.Y.Z] - YYYY-MM-DD". Without this the heading
# can ship bare, which is how 0.1.0 to 0.1.2 all went out with no date.
if [ "$snapshot" = 0 ]; then
  grep -qE "^## \[${version//./\\.}\] - [0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]*$" "$src/CHANGELOG.md" \
    || die "CHANGELOG.md: '## [$version]' needs its date: ## [$version] - $(date +%F)"
fi

# --- build (twice, to check it's reproducible) ----------------------------------------
# build DIR: the bundle, installer and notes, into DIR.
build() {
  local d=$1 p=$tmp/payload.$RANDOM sum f
  mkdir -p "$d"
  (cd "$src" && ./bundle.sh -o "$d/ryad" >/dev/null)
  mkdir -p "$p/bin" "$p/share/bash-completion/completions" "$p/share/doc/ryad"
  cp "$d/ryad" "$p/bin/ryad"
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
  } > "$d/ryad-installer.run"
  chmod 0755 "$d/ryad-installer.run"
  printf '%s\n' "$notes" > "$d/RELEASE_NOTES.md"
}
step "Build"
build "$tmp/a"
build "$tmp/b"
diff -r "$tmp/a" "$tmp/b" >/dev/null || die "two builds differ: the release isn't reproducible"

# --- test ------------------------------------------------------------------------------
step "Test the installer"
"$src/tests/installer-test.sh" "$tmp/a/ryad-installer.run" "$version"

# --- checksums, signature ---------------------------------------------------------------
rm -rf "$out"
mkdir -p "$out"
cp -a "$tmp/a/." "$out/"
(cd "$out" && sha256sum ryad ryad-installer.run > SHA256SUMS)
if [ "$snapshot" = 0 ]; then
  step "Sign SHA256SUMS with $key"
  ssh-keygen -Y sign -q -f "$key" -n file "$out/SHA256SUMS"
  # Check the signature as a user would, with the public key.
  printf 'ryad %s\n' "$(cat "$key.pub")" > "$tmp/allowed_signers"
  ssh-keygen -Y verify -f "$tmp/allowed_signers" -I ryad -n file -s "$out/SHA256SUMS.sig" \
    < "$out/SHA256SUMS" >/dev/null || die "the signature doesn't verify"
fi

# --- publish -----------------------------------------------------------------------------
publish_checks() {
  command -v gh >/dev/null || die "gh is needed to publish"
  git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null \
    || die "$tag isn't on origin yet: git push origin $tag"
}
if [ "$precheck" = 1 ]; then
  [ "$publish" = 0 ] || { step "Publish checks"; publish_checks; }
  step "Pre-check passed for ryad $version: nothing written to dist/, tagged nor uploaded"
  exit 0
fi

# --- tag ---------------------------------------------------------------------------------
# Only now that everything passed.
if [ "$snapshot" = 0 ] && [ "$publish" = 0 ]; then
  if [ "$already_tagged" = 1 ]; then
    step "Tag: HEAD is already $tag"
  else
    step "Tag $tag"
    git tag -a "$tag" -m "ryad $version" "$ref"
  fi
fi

step "Done: $out"
ls -l "$out" | tail -n +2 | sed 's/^/    /'
if [ "$snapshot" = 0 ] && [ "$publish" = 0 ]; then
  echo "    Next: git push origin main $tag, then: ./release.sh --key=FILE --publish"
fi

[ "$publish" = 1 ] || exit 0
publish_checks
read -r -p "Upload ryad $version to GitHub as a draft release? [y/N] " r
[[ $r == [yY]* ]] || { echo "not uploaded; the files are in $out"; exit 0; }
step "Draft release $tag"
gh release create "$tag" --draft --verify-tag --title "ryad $version" --notes-file "$out/RELEASE_NOTES.md" \
  "$out/ryad" "$out/ryad-installer.run" "$out/SHA256SUMS" "$out/SHA256SUMS.sig"
echo "    Review it on GitHub, then publish it there, or with: gh release edit $tag --draft=false"
