# Claude Desktop (official Linux beta) from Anthropic's apt repository.
# https://code.claude.com/docs/en/desktop-linux
#
# @description Claude Desktop, Anthropic's desktop app
# @commands claude-desktop
# @needs firefox
. "$(dirname "$0")/lib.sh"

KEY=/usr/share/keyrings/claude-desktop-archive-keyring.asc
FPR=31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE

curl -fsSLo "$KEY" https://downloads.claude.ai/claude-desktop/key.asc
gpg --show-keys --with-colons "$KEY" | grep -q "^fpr:::::::::$FPR:" \
  || die "signing key fingerprint mismatch (expected $FPR)"
echo "deb [arch=amd64,arm64 signed-by=$KEY] https://downloads.claude.ai/claude-desktop/apt/stable stable main" \
  > /etc/apt/sources.list.d/claude-desktop.list

apt-get update
v=${CLAUDE_DESKTOP_VERSION:-latest}
# --no-install-recommends: skips qemu/ovmf/virtiofsd (Cowork is not supported in the sandbox).
apt-get install -y --no-install-recommends "claude-desktop$([ "$v" = latest ] || echo "=$v")"
apt_clean

# Route claude:// deep links (sign-in callback) to the app.
desktop=$(grep -l 'x-scheme-handler/claude' /usr/share/applications/*.desktop 2>/dev/null | head -n1 || true)
if [ -n "$desktop" ]; then
  set_default_handler "$(basename "$desktop")" x-scheme-handler/claude
  update-desktop-database /usr/share/applications || true
fi

electron_wrapper claude-desktop /usr/bin/claude-desktop /usr/lib/claude-desktop/claude-desktop

installed=$(dpkg-query -W -f='${Version}' claude-desktop)
echo "CLAUDE_DESKTOP_VERSION=$installed" >> /etc/ryad-release
log "installed claude-desktop $installed"
