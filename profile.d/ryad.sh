# ryad: banner for interactive login shells (ryad <name>).
case $- in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac
if [ -n "${RYAD_NAME:-}" ]; then
  printf '\033[1mryad\033[0m %s · profile %s · workspace %s\n' \
    "'$RYAD_NAME'" "${RYAD_PROFILE:-?}" "${RYAD_WORKSPACE:-?}"
  # The commands of the image's apps (written by the build), plus emacs.
  if [ -r /etc/ryad/apps.list ]; then
    apps=$(cut -f2 /etc/ryad/apps.list | tr ' ' '\n')
  else
    apps="pi antigravity claude claude-desktop codium rstudio firefox"   # older images
  fi
  line=""
  for a in $apps emacs; do
    command -v "$a" >/dev/null 2>&1 && line="$line  $a"
  done
  printf '%s\n' "$line"
  unset apps line a
fi
