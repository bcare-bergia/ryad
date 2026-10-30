# ryad: Claude Desktop + Claude Code (+ editors) in a rootless container.
# Build with "ryad build" (resolves versions and passes the build args below).
#
# Layers are ordered from least to most frequently changing, so that upgrading
# Claude only rebuilds the last two layers:
#   1. apt packages from packages/*.list
#   2. user account
#   3. third-party apps (apps/<name>.sh, selected by APPS); "ryad build" replaces
#      the block between @apps-begin and @apps-end with one layer per app
#   4. Claude Desktop
#   5. Claude Code

# Any Debian/Ubuntu image (Claude Desktop ships as a .deb only):
# Ubuntu >= 22.04 or Debian >= 12.
ARG BASE_IMAGE=ubuntu:26.04
FROM ${BASE_IMAGE}
# Re-declare to make it visible for the LABEL below.
ARG BASE_IMAGE

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# --- 1. apt packages --------------------------------------------------------
# Set by `ryad build --refresh` to force a fresh apt layer (security updates).
ARG REFRESH=""
ARG EXTRA_PACKAGES=""
COPY packages/ /opt/ryad/packages/
RUN set -eu; \
    pkgs=$(sed 's/#.*//' /opt/ryad/packages/*.list | tr -s ' \t' '\n' | sed '/^$/d' | sort -u); \
    apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y --no-install-recommends $pkgs $EXTRA_PACKAGES; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

# --- 2. user ----------------------------------------------------------------
# UID/GID 1000 is what the launcher maps your host user to (--userns=keep-id).
# Recent Ubuntu images ship a user "ubuntu" with that UID: remove it.
# The user is renamed per environment at its first start (ryad
# --user=, see sbin/ryad-setuser), so sudo is granted by UID.
RUN set -eu; \
    u=$(getent passwd 1000 | cut -d: -f1 || true); \
    if [ -n "$u" ]; then userdel -r "$u" 2>/dev/null || userdel "$u"; fi; \
    g=$(getent group 1000 | cut -d: -f1 || true); \
    if [ -n "$g" ]; then groupdel "$g"; fi; \
    groupadd -g 1000 claude; \
    useradd -m -u 1000 -g 1000 -s /bin/bash claude; \
    echo '#1000 ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/claude; \
    chmod 0440 /etc/sudoers.d/claude; \
    install -d -m 0700 -o claude -g claude /run/user/1000

# --- 3. third-party apps ----------------------------------------------------
# @apps-begin
# All apps in one layer. "ryad build" replaces this block with one layer per
# app (COPY apps/lib.sh apps/<name>.sh, ARG <NAME>_VERSION, RUN), so adding,
# removing or upgrading one app doesn't reinstall the others.
COPY apps/ /opt/ryad/apps/
ARG APPS="firefox vscodium rstudio antigravity pi"
# Space-separated NAME_VERSION=value pairs, exported to app scripts.
ARG APP_VERSIONS=""
RUN set -eu; \
    for app in $APPS; do \
      [ -f "/opt/ryad/apps/$app.sh" ] || { echo "unknown app: $app" >&2; exit 1; }; \
      echo "### installing $app"; \
      env $APP_VERSIONS bash "/opt/ryad/apps/$app.sh"; \
    done
# @apps-end

# --- 4. Claude Desktop ------------------------------------------------------
COPY apps/lib.sh apps/claude-desktop.sh /opt/ryad/apps/
ARG CLAUDE_DESKTOP_VERSION=latest
RUN bash /opt/ryad/apps/claude-desktop.sh

# --- 5. Claude Code ---------------------------------------------------------
COPY apps/lib.sh apps/claude-code.sh /opt/ryad/apps/
ARG CLAUDE_CODE_VERSION=latest
RUN bash /opt/ryad/apps/claude-code.sh

# The installed apps, for the shell banner and "ryad apps":
# name<TAB>commands<TAB>description, from the @commands/@description lines of
# their scripts. Declared here so that changing APPS doesn't invalidate the
# layers above.
ARG APPS="firefox vscodium rstudio antigravity pi"
RUN set -eu; \
    mkdir -p /etc/ryad; \
    for app in claude-code claude-desktop $APPS; do \
      f=/opt/ryad/apps/$app.sh; \
      printf '%s\t%s\t%s\n' "$app" "$(sed -n 's/^# @commands //p' "$f" | head -n1)" \
        "$(sed -n 's/^# @description //p' "$f" | head -n1)"; \
    done > /etc/ryad/apps.list

LABEL org.ryad.base-image="${BASE_IMAGE}" \
      org.ryad.apps="${APPS}" \
      org.ryad.desktop-version="${CLAUDE_DESKTOP_VERSION}" \
      org.ryad.code-version="${CLAUDE_CODE_VERSION}"

ENV XDG_RUNTIME_DIR=/run/user/1000 \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    ELECTRON_OZONE_PLATFORM_HINT=auto \
    DISABLE_AUTOUPDATER=1 \
    GTK_USE_PORTAL=0

COPY --chmod=0644 profile.d/ryad.sh /etc/profile.d/ryad.sh
COPY --chmod=0644 profile.d/prompt.sh /etc/ryad/prompt.sh
RUN echo '. /etc/ryad/prompt.sh' >> /etc/bash.bashrc
COPY --chmod=0755 sbin/ryad-setuser /usr/local/sbin/ryad-setuser
COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh
USER claude
WORKDIR /home/claude
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["idle"]

# Which ryad bundle built this image ("<version> <stamp>", or "source"). Last,
# so that a new stamp doesn't invalidate any cached layer.
ARG RYAD_LAUNCHER=""
LABEL org.ryad.launcher="${RYAD_LAUNCHER}"
