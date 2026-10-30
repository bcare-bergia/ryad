#!/usr/bin/env bash
# Build the ryad image from this checkout: same as 'ryad build', with the
# build files of this folder. Options: ./build.sh --help.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
exec ./ryad build --context=. "$@"
