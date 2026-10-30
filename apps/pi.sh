# Pi coding agent (https://pi.dev) from npm, installed system-wide in /opt/pi.
# Same package as https://pi.dev/install.sh, without the per-user install (the
# home directory is the profile; Pi keeps its settings and logins in ~/.pi).
# Needs Node.js >= 22.19: the distro's if recent enough (Ubuntu 26.04), else
# the current Node.js 22 LTS from nodejs.org, used by pi only.
#
# @description Pi coding agent (terminal)
# @commands pi
# @needs firefox
# @latest curl -fsSL https://registry.npmjs.org/@earendil-works/pi-coding-agent/latest | jq -r .version
. "$(dirname "$0")/lib.sh"

PKG=@earendil-works/pi-coding-agent
v=${PI_VERSION:-latest}
[ "$v" = latest ] && v=$(curl -fsSL "https://registry.npmjs.org/$PKG/latest" | jq -r .version)
[[ $v =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || die "bad version '$v'"

node_ok() { # <node binary>
  "$1" -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 19) ? 0 : 1)' 2>/dev/null
}

nodebin=""
if command -v node >/dev/null && command -v npm >/dev/null && node_ok node; then
  log "using the distro's Node.js $(node --version)"
else
  case $ARCH in amd64) narch=x64 ;; arm64) narch=arm64 ;; *) die "unsupported arch $ARCH" ;; esac
  dist=https://nodejs.org/dist/latest-v22.x
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/SHASUMS256.txt" "$dist/SHASUMS256.txt"
  file=$(awk -v s="-linux-$narch.tar.xz" 'index($2, s) && $2 ~ /^node-v/ { print $2 }' "$tmp/SHASUMS256.txt")
  [ -n "$file" ] || die "no Node.js 22 build for linux-$narch"
  log "distro Node.js is missing or older than 22.19: installing $file"
  curl -fsSL -o "$tmp/$file" "$dist/$file"
  (cd "$tmp" && grep " $file\$" SHASUMS256.txt | sha256sum -c - >/dev/null) || die "Node.js checksum mismatch"
  install -d /opt/pi/node
  tar -xJ --strip-components=1 -C /opt/pi/node -f "$tmp/$file"
  rm -rf "$tmp"
  nodebin=/opt/pi/node/bin
fi

# --ignore-scripts: as recommended by pi.dev, no dependency install scripts.
PATH=${nodebin:+$nodebin:}$PATH npm install -g --prefix /opt/pi --ignore-scripts --no-fund --no-audit "$PKG@$v"
npm cache clean --force 2>/dev/null || true
rm -rf /root/.npm

main=/opt/pi/lib/node_modules/$PKG/$(jq -r '.bin.pi' "/opt/pi/lib/node_modules/$PKG/package.json")
[ -f "$main" ] || die "pi entry point not found"
cat > /usr/local/bin/pi <<WRAP
#!/bin/sh
${nodebin:+PATH=$nodebin:\$PATH; export PATH
}exec node $main "\$@"
WRAP
chmod 0755 /usr/local/bin/pi
log "installed pi $v"
