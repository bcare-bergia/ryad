# ryad: banner for interactive login shells (ryad <name>).
case $- in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac
if [ -n "${RYAD_NAME:-}" ]; then
  printf '\033[1mryad\033[0m %s · profile %s · workspace %s\n' \
    "'$RYAD_NAME'" "${RYAD_PROFILE:-?}" "${RYAD_WORKSPACE:-?}"
  apps=""
  for a in pi antigravity claude claude-desktop codium rstudio emacs firefox; do
    command -v "$a" >/dev/null 2>&1 && apps="$apps  $a"
  done
  printf '%s\n' "$apps"
fi
