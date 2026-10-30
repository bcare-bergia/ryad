# Claude Code CLI, native binary, installed system-wide in /opt/claude-code.
# Same source and checksum verification as https://claude.ai/install.sh, but
# without the per-user shell integration (the home directory is the profile).
. "$(dirname "$0")/lib.sh"

BASE=https://downloads.claude.ai/claude-code-releases
v=${CLAUDE_CODE_VERSION:-latest}
case $v in latest|stable) v=$(curl -fsSL "$BASE/$v") ;; esac
[[ $v =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || die "bad version '$v'"

case $(uname -m) in x86_64|amd64) arch=x64 ;; aarch64|arm64) arch=arm64 ;; *) die "unsupported arch" ;; esac
platform=linux-$arch
ldd /bin/ls 2>&1 | grep -q musl && platform+=-musl

sum=$(curl -fsSL "$BASE/$v/manifest.json" | jq -r --arg p "$platform" '.platforms[$p].checksum // empty')
[ -n "$sum" ] || die "no checksum for $platform in $v manifest"

install -d /opt/claude-code
curl -fsSL -o "/opt/claude-code/claude-$v" "$BASE/$v/$platform/claude"
echo "$sum  /opt/claude-code/claude-$v" | sha256sum -c - >/dev/null || die "checksum mismatch"
chmod 0755 "/opt/claude-code/claude-$v"
ln -sf "/opt/claude-code/claude-$v" /usr/local/bin/claude

echo "CLAUDE_CODE_VERSION=$v" >> /etc/ryad-release
log "installed claude-code $v"
