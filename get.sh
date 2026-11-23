#!/bin/bash
# =====================================================================
#  Proxlafy · install from GitHub (one command, on the Raspberry Pi)
#  Proxlafy · instalación desde GitHub (un solo comando, en la Raspberry)
#
#     curl -fsSL https://raw.githubusercontent.com/romartak/proxlafy/main/get.sh | sudo bash
#
#  Downloads the project to /opt/proxlafy-src and runs the installer.
#  Descarga el proyecto en /opt/proxlafy-src y ejecuta el instalador.
#  Update later · Para actualizar después:  sudo proxlafy update  (sudo proxlafy actualizar)
# =====================================================================
set -o pipefail
REPO="${PROXLAFY_REPO:-https://github.com/romartak/proxlafy.git}"
BRANCH="${PROXLAFY_BRANCH:-main}"
SRC=/opt/proxlafy-src

GL="${PROXLAFY_LANG:-}"
for v in "${LC_ALL:-}" "${LC_MESSAGES:-}" "${LANG:-}"; do
  case "$v" in ''|C|C.*|POSIX) ;; *) [ -n "$GL" ] || GL="$v" ;; esac
done
case "$GL" in [Ee][Ss]*|[Ss][Pp]*) GL=es ;; *) GL=en ;; esac
L() { if [ "$GL" = es ]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi; }

[ "$(id -u)" -eq 0 ] || { L "Run with sudo:  curl -fsSL …/get.sh | sudo bash" "Ejecuta con sudo:  curl -fsSL …/get.sh | sudo bash"; exit 1; }
L "==> Proxlafy: downloading $REPO (branch $BRANCH)…" "==> Proxlafy: descargando $REPO (rama $BRANCH)…"
if ! command -v git >/dev/null; then
  apt-get update -qq && apt-get install -y -qq git || { L "✖ Could not install git (internet?)." "✖ No se pudo instalar git (¿internet?)."; exit 1; }
fi
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" remote set-url origin "$REPO"
  git -C "$SRC" fetch -q --depth 100 origin "$BRANCH" && git -C "$SRC" reset -q --hard FETCH_HEAD \
    || { L "✖ Could not update the local copy." "✖ No se pudo actualizar la copia local."; exit 1; }
else
  rm -rf "$SRC"
  git clone -q --depth 100 -b "$BRANCH" "$REPO" "$SRC" || { L "✖ Could not download $REPO." "✖ No se pudo descargar $REPO."; exit 1; }
fi
L "==> Version $(cat "$SRC/VERSION" 2>/dev/null) downloaded. Starting the installer…" \
  "==> Versión $(cat "$SRC/VERSION" 2>/dev/null) descargada. Iniciando el instalador…"
if { true </dev/tty; } 2>/dev/null; then
  exec bash "$SRC/install.sh" </dev/tty
else
  exec bash "$SRC/install.sh"
fi
