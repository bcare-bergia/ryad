# Google Antigravity (desktop app) from Google's release tarball, in /opt/antigravity.
# https://antigravity.google/download?os=linux
# (The older apt repository only has the legacy 1.x IDE.)
#
# @description Google Antigravity, agent-first IDE
# @commands antigravity
# @needs firefox
# @latest curl -fsSL https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases | jq -r '.[0].version'
. "$(dirname "$0")/lib.sh"

RELEASES=https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases
BASE=https://storage.googleapis.com/antigravity-public/antigravity-hub

case $ARCH in amd64) platform=linux-x64 ;; arm64) platform=linux-arm ;; *) die "unsupported arch $ARCH" ;; esac

# Each version is published under <version>-<execution id>.
v=${ANTIGRAVITY_VERSION:-latest}
releases=$(curl -fsSL "$RELEASES")
[ "$v" = latest ] && v=$(jq -r '.[0].version' <<<"$releases")
id=$(jq -r --arg v "$v" 'first(.[] | select(.version == $v) | .execution_id) // empty' <<<"$releases")
[ -n "$id" ] || die "unknown version '$v'"

# Electron's runtime libraries (a .deb would pull them in; the tarball doesn't).
# Newer distros renamed some of them <name>t64 (64-bit time_t transition).
apt-get update
pkgs=()
for p in libgtk-3-0 libnss3 libasound2 libgbm1 libxss1 libsecret-1-0 libcups2 libxkbcommon0 xdg-utils; do
  apt-cache show "${p}t64" >/dev/null 2>&1 && p+=t64
  pkgs+=("$p")
done
apt-get install -y --no-install-recommends "${pkgs[@]}"
apt_clean

url="$BASE/$v-$id/$platform/Antigravity.tar.gz"
log "downloading $url"
rm -rf /opt/antigravity
install -d /opt/antigravity
curl -fsSL "$url" | tar -xz --strip-components=1 -C /opt/antigravity
[ -x /opt/antigravity/antigravity ] || die "no antigravity binary in $url"
# Chromium's sandbox helper must be setuid root (as the .deb packages do it).
chown root:root /opt/antigravity/chrome-sandbox
chmod 4755 /opt/antigravity/chrome-sandbox

# Desktop file, so that antigravity:// sign-in links reach the app.
cat > /usr/share/applications/antigravity.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Antigravity
Comment=Google Antigravity
Exec=antigravity %U
Terminal=false
Categories=Development;
MimeType=x-scheme-handler/antigravity;
DESKTOP
set_default_handler antigravity.desktop x-scheme-handler/antigravity
update-desktop-database /usr/share/applications || true

electron_wrapper antigravity /opt/antigravity/antigravity /opt/antigravity/antigravity
log "installed antigravity $v"
