#!/bin/bash
# =====================================================================
#  Proxlafy · updater · actualizador
#  Gets the latest version from GitHub and installs it WITHOUT touching your settings
#  (/etc/proxlafy/proxlafy.conf) or your data (the card library, logs).
#  Checks the new panel answers and ROLLS BACK automatically if it does not.
#  Trae la última versión desde GitHub, comprueba que arranca y, si no, VUELVE SOLO a la anterior.
#
#  sudo proxlafy update          check, show changes and ask · busca, muestra cambios y pregunta
#  sudo proxlafy update --yes    no questions (panel button) · sin preguntar   (--si)
#  sudo proxlafy update --force  reinstall even if up to date · reinstala aunque esté al día  (--forzar)
#  proxlafy update --check       only report whether there is something new (--json)   (--buscar)
#  sudo proxlafy rollback        go back to the previous version · versión anterior   (volver)
# =====================================================================
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=proxlafy-lib.sh
source "$HERE/proxlafy-lib.sh" 2>/dev/null || source /opt/proxlafy/proxlafy-lib.sh
CONF=/etc/proxlafy/proxlafy.conf
SRC=/opt/proxlafy-src
OPT=/opt/proxlafy
STATE=/var/lib/proxlafy
LOG=/var/log/proxlafy-update.log
proxlafy_load_conf "$CONF"
proxlafy_lang_init

MODE=apply; YES=no; FORCE=no; JSON=no
for a in "$@"; do
  case "$a" in
    --buscar|--check) MODE=check ;;
    --volver|--rollback) MODE=rollback ;;
    --si|--yes|-y) YES=yes ;;
    --forzar|--force) FORCE=yes ;;
    --json) JSON=yes ;;
  esac
done

REPO="${PROXLAFY_REPO:-}"
[ -n "$REPO" ] || REPO="$(git -C "$SRC" remote get-url origin 2>/dev/null)"
[ -n "$REPO" ] || REPO="$PROXLAFY_DEFAULT_REPO"
BRANCH="${PROXLAFY_BRANCH:-main}"

say()  { [ "$JSON" = yes ] || L "$@"; }
jstr() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }
die()  { local m; m="$(L "$1" "$2")"
  if [ "$JSON" = yes ]; then echo "{\"ok\": false, \"online\": ${3:-true}, \"error\": $(jstr "$m")}"; exit 1; fi
  echo "✖ $m"; exit 1; }

current_commit()  { cat "$STATE/commit" 2>/dev/null; }
current_version() { cat "$OPT/VERSION" 2>/dev/null || echo "?"; }

# ---------------------------------------------------------------- rollback · volver
if [ "$MODE" = rollback ]; then
  [ "$(id -u)" -eq 0 ] || die "Use: sudo proxlafy rollback" "Usa: sudo proxlafy volver"
  [ -d "$OPT.prev" ] || die "There is no previous version saved." "No hay una versión anterior guardada."
  prev_ver="$(cat "$OPT.prev/VERSION" 2>/dev/null || echo '?')"
  L "Going back to the previous version ($prev_ver)…" "Volviendo a la versión anterior ($prev_ver)…"
  rm -rf "$OPT.tmp" && mv "$OPT" "$OPT.tmp" && mv "$OPT.prev" "$OPT" && mv "$OPT.tmp" "$OPT.prev"
  [ -f "$OPT/proxlafy-cli.sh" ] && install -m 755 "$OPT/proxlafy-cli.sh" /usr/local/bin/proxlafy
  prev="$(cat "$STATE/prev_commit" 2>/dev/null)"; cur="$(current_commit)"
  [ -n "$prev" ] && echo "$prev" > "$STATE/commit"; [ -n "$cur" ] && echo "$cur" > "$STATE/prev_commit"
  systemctl restart proxlafy && L "✔ Done: version $(current_version)." "✔ Listo: versión $(current_version)."
  exit 0
fi

# ---------------------------------------------------------------- fetch from GitHub
[ "$MODE" = check ] || [ "$(id -u)" -eq 0 ] || die "Use: sudo proxlafy update" "Usa: sudo proxlafy actualizar"
# Self-heal the common "no internet" cause (broken router DNS / dead IPv6) before checking.
if [ "$(id -u)" -eq 0 ] && command -v proxlafy_harden_dns >/dev/null 2>&1; then
  proxlafy_harden_dns >/dev/null 2>&1 && sleep 2 || true
fi
# Prefer IPv4: many home routers hand out IPv6 without a working route, which makes a plain
# curl hang and look like "no internet". -4 avoids that; if it still fails, there is really no path.
if ! curl -4 -fsS --max-time 12 -o /dev/null "https://github.com" 2>/dev/null \
   && ! curl -fsS --max-time 12 -o /dev/null "https://github.com" 2>/dev/null; then
  die "No internet. Connect the Pi to WiFi (home or phone hotspot) and try again." \
      "Sin internet. Conecta la Raspberry a una WiFi (casa o hotspot del celular) y reintenta." false
fi
command -v git >/dev/null || die "git is missing: sudo apt install git" "Falta git: sudo apt install git"
GIT=(git -C "$SRC" -c advice.detachedHead=false)

if [ ! -d "$SRC/.git" ]; then
  say "Downloading the project from $REPO …" "Descargando el proyecto desde $REPO …"
  rm -rf "$SRC"
  git clone -q --depth 100 -b "$BRANCH" "$REPO" "$SRC" 2>&1 \
    || die "Could not download $REPO (does it exist?)." "No se pudo descargar $REPO (¿existe?)."
else
  "${GIT[@]}" remote set-url origin "$REPO"
fi
"${GIT[@]}" fetch -q --depth 100 origin "$BRANCH" 2>&1 \
  || die "Could not reach GitHub ($REPO, branch $BRANCH)." "No se pudo consultar GitHub ($REPO, rama $BRANCH)."
NEW="$("${GIT[@]}" rev-parse FETCH_HEAD)"
OLD="$(current_commit)"
NEW_VER="$("${GIT[@]}" show "$NEW:VERSION" 2>/dev/null | tr -d '[:space:]')"
NEW_REV="$("${GIT[@]}" show "$NEW:install.sh" 2>/dev/null | sed -n 's/^INSTALL_REV=\([0-9]*\).*/\1/p' | head -1)"
CUR_REV="$(cat "$STATE/install_rev" 2>/dev/null || echo 0)"
FULL=no; [ "${NEW_REV:-0}" -gt "${CUR_REV:-0}" ] 2>/dev/null && FULL=yes
if [ -n "$OLD" ] && "${GIT[@]}" cat-file -e "$OLD^{commit}" 2>/dev/null; then
  CHANGES="$("${GIT[@]}" log --format='%s' "$OLD..$NEW" 2>/dev/null)"
else
  CHANGES="$("${GIT[@]}" log --format='%s' -n 10 "$NEW" 2>/dev/null)"
fi
BEHIND=0; [ "$NEW" != "$OLD" ] && BEHIND="$(printf '%s\n' "$CHANGES" | grep -c .)"
[ "$NEW" != "$OLD" ] && [ "$BEHIND" -eq 0 ] && BEHIND=1

if [ "$MODE" = check ]; then
  if [ "$JSON" = yes ]; then
    python3 - "$(current_version)" "$OLD" "$NEW_VER" "$NEW" "$BEHIND" "$FULL" "$CHANGES" "$REPO" "$BRANCH" <<'PY'
import json, sys
cv, oc, nv, nc, behind, full, changes, repo, branch = sys.argv[1:]
print(json.dumps({"ok": True, "online": True, "current": cv, "current_commit": oc[:7], "latest": nv or "?",
                  "latest_commit": nc[:7], "behind": int(behind), "full": full == "yes",
                  "changes": [c for c in changes.splitlines() if c][:30], "repo": repo, "branch": branch}))
PY
  elif [ "$BEHIND" -eq 0 ]; then
    L "✔ Already up to date ($(current_version))." "✔ Ya tienes la última versión ($(current_version))."
  else
    L "Update available: $(current_version) → ${NEW_VER:-?}  ($BEHIND changes)" \
      "Hay una actualización: $(current_version) → ${NEW_VER:-?}  ($BEHIND cambios)"
    printf '%s\n' "$CHANGES" | head -15 | sed 's/^/  • /'
    L "To install it:  sudo proxlafy update" "Para instalarla:  sudo proxlafy actualizar"
  fi
  exit 0
fi

# ---------------------------------------------------------------- install · instalar
exec 9>/run/proxlafy-update.lock
flock -n 9 || die "An update is already running." "Ya hay una actualización en curso."
exec > >(tee -a "$LOG") 2>&1
echo
L "=== Update $(date '+%F %T') ===" "=== Actualización $(date '+%F %T') ==="
if [ "$BEHIND" -eq 0 ] && [ "$FORCE" != yes ]; then
  L "✔ Already up to date ($(current_version)). (Reinstall: sudo proxlafy update --force)" \
    "✔ Ya tienes la última versión ($(current_version)). (Reinstalar: sudo proxlafy actualizar --forzar)"
  exit 0
fi
L "Installed: $(current_version)   →   new: ${NEW_VER:-?}" "Instalada: $(current_version)   →   nueva: ${NEW_VER:-?}"
[ -n "$CHANGES" ] && { L "Changes:" "Cambios:"; printf '%s\n' "$CHANGES" | head -20 | sed 's/^/  • /'; }
if [ "$YES" != yes ] && [ -t 0 ]; then
  proxlafy_ask_yn "Update now?" "¿Actualizar ahora?" yes || { L "Cancelled." "Cancelado."; exit 0; }
fi

# backup of what works now · copia de lo que funciona ahora
rm -rf "$OPT.prev"
[ -d "$OPT" ] && cp -a "$OPT" "$OPT.prev"
cp -a "$CONF" "$CONF.antes-de-actualizar" 2>/dev/null
[ -n "$OLD" ] && echo "$OLD" > "$STATE/prev_commit"
"${GIT[@]}" reset -q --hard "$NEW" && "${GIT[@]}" clean -qfd || die "Could not prepare the new version." "No se pudo preparar la versión nueva."

rollback() {  # "English" "Español"
  echo "✖ $(L "$1" "$2")"
  if [ -d "$OPT.prev" ]; then
    rm -rf "$OPT" && mv "$OPT.prev" "$OPT"
    [ -f "$OPT/proxlafy-cli.sh" ] && install -m 755 "$OPT/proxlafy-cli.sh" /usr/local/bin/proxlafy
    [ -n "$OLD" ] && "${GIT[@]}" reset -q --hard "$OLD" 2>/dev/null
    [ -n "$OLD" ] && echo "$OLD" > "$STATE/commit"
    echo "$CUR_REV" > "$STATE/install_rev"
    systemctl restart proxlafy
    L "↩ Rolled back to $(current_version): everything is as before." \
      "↩ Volví a $(current_version): todo sigue como antes."
  fi
  exit 1
}
wait_panel() {
  local code
  for _ in $(seq 1 30); do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:${PANEL_PORT:-80}/api/status")"
    case "$code" in 200|401) return 0 ;; esac
    sleep 2
  done
  return 1
}

if [ "$FULL" = yes ]; then
  L "Full installation (new packages); it ends with a reboot…" "Instalación completa (paquetes nuevos); al final reinicia…"
  SDRKIT_NO_REBOOT=1 PROXLAFY_NO_REBOOT=1 bash "$SRC/install.sh" </dev/null || rollback "The full installation failed." "Falló la instalación completa."
  wait_panel || rollback "The new panel did not answer within 60 s." "El panel nuevo no respondió en 60 s."
  echo "$NEW" > "$STATE/commit"
  L "✔ Updated to $(current_version). Rebooting in 15 s." "✔ Actualizado a $(current_version). Reinicia en 15 s."
  sync; sleep 15; systemctl reboot
  exit 0
fi

bash "$SRC/install.sh" --panel || rollback "Installing the new version failed." "Falló la instalación de la versión nueva."
L "Checking that the panel starts…" "Comprobando que el panel arranca…"
if wait_panel; then
  echo "$NEW" > "$STATE/commit"
  L "✔ Updated to $(current_version). Reload the panel on your phone." \
    "✔ Actualizado a $(current_version). Recarga el panel en el celular."
  exit 0
fi
rollback "The new panel did not answer within 60 s." "El panel nuevo no respondió en 60 s."
