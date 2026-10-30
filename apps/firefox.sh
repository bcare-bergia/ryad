# Firefox from Mozilla's apt repository (Ubuntu's own "firefox" is a snap stub).
# Used as the in-container browser for OAuth sign-in (claude /login, Claude Desktop).
#
# @description Firefox web browser; opens the other apps' sign-in pages
# @commands firefox
. "$(dirname "$0")/lib.sh"

install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg -o /etc/apt/keyrings/packages.mozilla.org.asc
echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" \
  > /etc/apt/sources.list.d/mozilla.list
# Prefer Mozilla's package over the distro's snap transitional package.
cat > /etc/apt/preferences.d/mozilla <<'PIN'
Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000
PIN

apt-get update
v=${FIREFOX_VERSION:-latest}
apt-get install -y --no-install-recommends "firefox$([ "$v" = latest ] || echo "=$v")"
apt_clean

update-alternatives --set x-www-browser /usr/bin/firefox 2>/dev/null || true
set_default_handler firefox.desktop text/html x-scheme-handler/http x-scheme-handler/https \
  x-scheme-handler/about x-scheme-handler/unknown
log "installed $(firefox --version 2>/dev/null || echo firefox)"
