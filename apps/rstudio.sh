# RStudio Desktop from Posit's .deb. R itself comes from packages/20-dev.list.
#
# @description RStudio Desktop, IDE for R
# @commands rstudio
# @latest k=$BASE_CODENAME; [ "$BASE_ID" != debian ] || k=debian${BASE_VERSION%%.*}; curl -fsSL https://www.rstudio.com/wp-content/downloads.json | jq -r --arg k "$k" '.rstudio.open_source.stable.desktop.installer as $i | ($i[$k] // $i.jammy).url' | sed -E 's|.*/rstudio-([0-9.]+-[0-9]+)-[a-z0-9_]+\.deb$|\1|'
. "$(dirname "$0")/lib.sh"

v=${RSTUDIO_VERSION:-latest}
if [ "$v" = latest ]; then
  json=$(curl -fsSL https://www.rstudio.com/wp-content/downloads.json)
  key=$CODENAME
  [ "$ID" = debian ] && key="debian${VERSION_ID%%.*}"
  url=$(jq -r --arg k "$key" '.rstudio.open_source.stable.desktop.installer[$k].url // empty' <<<"$json")
  [ -n "$url" ] || url=$(jq -r '.rstudio.open_source.stable.desktop.installer.jammy.url' <<<"$json")
  url=${url/\/amd64\//\/$ARCH\/}; url=${url/-amd64.deb/-$ARCH.deb}
else
  url="https://download1.rstudio.org/electron/jammy/$ARCH/rstudio-$v-$ARCH.deb"
fi

log "downloading $url"
tmp=$(mktemp -d)
curl -fsSL -o "$tmp/rstudio.deb" "$url"
apt-get update
apt-get install -y --no-install-recommends "$tmp/rstudio.deb"
rm -rf "$tmp"
apt_clean
electron_wrapper rstudio /usr/bin/rstudio /usr/lib/rstudio/rstudio
log "installed rstudio $(dpkg-query -W -f='${Version}' rstudio)"
