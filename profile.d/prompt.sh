# ryad: prompt colors (sourced from /etc/bash.bashrc).
# Set per profile with PROMPT_COLORS=... in profile.conf; the launcher passes it
# as RYAD_PROMPT_COLORS each time you enter. Unset: prompt untouched.
#   PROMPT_COLORS="user=bold-green host=yellow dir=1;34"
# Elements: user host dir. Colors: black red green yellow blue magenta cyan
# white, bright-<color>, with an optional bold- prefix; default; or raw SGR
# codes such as 01;32. Elements left out keep Ubuntu's colors.
[ -n "${PS1:-}" ] && [ -n "${RYAD_PROMPT_COLORS:-}" ] || return 0

__cs_sgr() { # <color>: print its SGR code
  local c=$1 pre="" base=30 i=0 n
  if [[ $c =~ ^[0-9]+(;[0-9]+)*$ ]]; then echo "$c"; return 0; fi
  [ "$c" = default ] && { echo 0; return 0; }
  case $c in bold-*) pre="1;" c=${c#bold-} ;; esac
  case $c in bright-*) base=90 c=${c#bright-} ;; esac
  for n in black red green yellow blue magenta cyan white; do
    [ "$n" = "$c" ] && { echo "$pre$((base + i))"; return 0; }
    i=$((i + 1))
  done
  return 1
}

__cs_build_ps1() {
  local u='01;32' h='01;32' d='01;34' tok code toks IFS=', '
  read -ra toks <<< "$RYAD_PROMPT_COLORS"
  for tok in "${toks[@]}"; do
    if [[ $tok == *=* ]] && code=$(__cs_sgr "${tok#*=}"); then
      case ${tok%%=*} in
        user) u=$code ;; host) h=$code ;; dir) d=$code ;;
        *) echo "ryad: ignoring prompt color '$tok' (elements: user host dir)" >&2 ;;
      esac
    else
      echo "ryad: ignoring prompt color '$tok'" >&2
    fi
  done
  __cs_ps1='${debian_chroot:+($debian_chroot)}\[\e['"$u"'m\]\u\[\e[0m\]@\[\e['"$h"'m\]\h\[\e[0m\]:\[\e['"$d"'m\]\w\[\e[0m\]\$ '
  case ${TERM:-} in
    xterm*|rxvt*) __cs_ps1='\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]'"$__cs_ps1" ;;
  esac
}

# ~/.bashrc (from the profile) runs after this file and sets its own PS1, so
# apply ours from a one-shot PROMPT_COMMAND hook, i.e. after all rc files.
__cs_set_ps1() {
  PS1=$__cs_ps1
  PROMPT_COMMAND=${PROMPT_COMMAND#__cs_set_ps1}
  PROMPT_COMMAND=${PROMPT_COMMAND#;}
  unset __cs_ps1
  unset -f __cs_set_ps1 __cs_sgr __cs_build_ps1
}

__cs_build_ps1
PROMPT_COMMAND=__cs_set_ps1${PROMPT_COMMAND:+;$PROMPT_COMMAND}
