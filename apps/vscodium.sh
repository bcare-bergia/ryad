# VSCodium (open-source VS Code build) from its apt repository.
#
# @description VSCodium, the open-source build of VS Code
# @commands codium
# shellcheck shell=bash
. "$(dirname "$0")/lib.sh"

curl -fsSL https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg \
  | gpg --dearmor -o /usr/share/keyrings/vscodium-archive-keyring.gpg
echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/vscodium-archive-keyring.gpg] https://download.vscodium.com/debs vscodium main" \
  > /etc/apt/sources.list.d/vscodium.list

apt-get update
v=${VSCODIUM_VERSION:-latest}
apt-get install -y --no-install-recommends "codium$([ "$v" = latest ] || echo "=$v")"
apt_clean
electron_wrapper codium /usr/bin/codium /usr/share/codium/codium
log "installed codium $(dpkg-query -W -f='${Version}' codium)"
