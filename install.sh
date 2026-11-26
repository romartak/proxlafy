#!/bin/bash
# =====================================================================
#  Proxlafy · installer · instalador
#  Raspberry Pi Zero 2 W + Proxmark3 (Iceman) + power bank  →  web panel
#  to read, clone and emulate RFID cards (LF 125 kHz + HF 13.56 MHz),
#  with an automatic WiFi hotspot.  Private-lab / authorized use.
#  Panel web para leer, clonar y emular tarjetas RFID, con hotspot WiFi
#  automático.  Uso de laboratorio privado / autorizado.
#
#  On the Pi (over SSH) · En la Raspberry (por SSH):
#     curl -fsSL https://raw.githubusercontent.com/romartak/proxlafy/main/get.sh | sudo bash
#
#  install.sh --panel   panel-only update (used by "proxlafy update")
# =====================================================================
set -o pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=/var/log/proxlafy-install.log
ETC=/etc/proxlafy
CONF="$ETC/proxlafy.conf"
OPT=/opt/proxlafy
STATE_DIR=/var/lib/proxlafy
STAGE="${1:-}"

c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_b=$'\e[1m'; c_0=$'\e[0m'
[ -f "$KIT/files/proxlafy-lib.sh" ] && [ -f "$KIT/files/proxlafy_server.py" ] || {
  echo "${c_err}  ✖ $KIT/files/ not found: copy the whole proxlafy folder.${c_0}"; exit 1; }
# shellcheck source=files/proxlafy-lib.sh
source "$KIT/files/proxlafy-lib.sh"

say()  { proxlafy_pick "$@"; echo "${c_b}==>${c_0} $REPLY"; }
ok()   { proxlafy_pick "$@"; echo "${c_ok}  ✔${c_0} $REPLY"; }
warn() { proxlafy_pick "$@"; echo "${c_warn}  ⚠${c_0} $REPLY"; }
die()  { proxlafy_pick "$@"; echo "${c_err}  ✖ $REPLY${c_0}"; exit 1; }

case "$STAGE" in
  --panel) PROXLAFY_LANG="$(proxlafy_conf_lang "$CONF")" ;;
  *) [ -f "$CONF" ] && PROXLAFY_LANG="$(proxlafy_conf_lang "$CONF")" || PROXLAFY_LANG="$(proxlafy_conf_lang "$KIT/proxlafy.conf")" ;;
esac
proxlafy_lang_init
[ "$(id -u)" -eq 0 ] || die "Run it with sudo:  sudo bash $0" "Ejecuta con sudo:  sudo bash $0"

# Bump when a new version needs packages/system changes: "proxlafy update" then does the full install.
# Súbelo cuando una versión necesite paquetes/cambios del sistema: «proxlafy actualizar» hará la completa.
INSTALL_REV=1
APT=(apt-get -y -o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confold)
export DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------------------
# Copies the panel to /opt/proxlafy and (re)installs the service.
# Copia el panel a /opt/proxlafy y (re)instala el servicio.
install_panel() {
  mkdir -p "$OPT" "$STATE_DIR" "$ETC"
  cp -a "$KIT/files/." "$OPT/"
  cp -a "$KIT/VERSION" "$OPT/VERSION" 2>/dev/null
  chmod 755 "$OPT/proxlafy-cli.sh" "$OPT/proxlafy-update.sh" "$OPT/proxlafy-netwatch.sh" 2>/dev/null
  install -m 755 "$OPT/proxlafy-cli.sh" /usr/local/bin/proxlafy
  [ -f "$OPT/labswitch.sh" ] && install -m 755 "$OPT/labswitch.sh" /usr/local/sbin/labswitch
  install -m 644 "$OPT/proxlafy.service" /etc/systemd/system/proxlafy.service
  install -m 644 "$OPT/proxlafy-netwatch.service" /etc/systemd/system/proxlafy-netwatch.service
  systemctl daemon-reload
}

# If SDR-Kit (the other lab project) is installed and running, pause it so Proxlafy
# can take the hotspot and port 80. It stays installed; switch back any time.
# Si SDR-Kit (el otro proyecto) está instalado y activo, lo pausamos para que Proxlafy
# tome el hotspot y el puerto 80. Queda instalado; puedes volver cuando quieras.
pause_other_project() {
  [ -f /etc/systemd/system/sdrkit.service ] || return 0
  if systemctl is-active --quiet sdrkit 2>/dev/null || systemctl is-enabled --quiet sdrkit 2>/dev/null; then
    systemctl disable --now sdrkit sdrkit-netwatch >/dev/null 2>&1
    nmcli connection down sdrkit-hotspot >/dev/null 2>&1
    ok "SDR-Kit paused (switch back: sudo labswitch sdrkit)." "SDR-Kit pausado (vuelve con: sudo labswitch sdrkit)."
  fi
}

merge_conf_from_kit() {
  local n
  if [ ! -f "$CONF" ]; then cp "$KIT/proxlafy.conf" "$CONF"; ok "Configuration created: $CONF" "Configuración creada: $CONF"; return; fi
  n=$(proxlafy_merge_conf "$KIT/proxlafy.conf" "$CONF")
  [ "$n" -gt 0 ] 2>/dev/null && ok "$n new option(s) added to $CONF" "$n opción(es) nueva(s) agregadas a $CONF" || true
}

record_rev() { echo "$INSTALL_REV" > "$STATE_DIR/install_rev"; }

# ---------------------------------------------------------------------
#  QUICK UPDATE (panel only) · ACTUALIZACIÓN RÁPIDA (sólo el panel)
# ---------------------------------------------------------------------
if [ "$STAGE" = "--panel" ]; then
  mkdir -p "$STATE_DIR"
  merge_conf_from_kit
  install_panel
  record_rev
  systemctl restart proxlafy
  exit 0   # the updater records the commit once the panel answers
fi

# ---------------------------------------------------------------------
#  FULL INSTALL · INSTALACIÓN COMPLETA
# ---------------------------------------------------------------------
exec > >(tee -a "$LOG") 2>&1
mkdir -p "$ETC" "$STATE_DIR"

# --- language · idioma ---
if [ -z "$(proxlafy_norm_lang "${PROXLAFY_LANG:-}")" ]; then
  echo "Language / Idioma:  [1] English   [2] Español"
  read -r -p "> " a; case "$a" in 2) PROXLAFY_LANG=es ;; *) PROXLAFY_LANG=en ;; esac
  proxlafy_lang_init
fi

# --- create config from template and ask for the essentials ---
[ -f "$CONF" ] || cp "$KIT/proxlafy.conf" "$CONF"
merge_conf_from_kit
proxlafy_set_conf PROXLAFY_LANG "$PROXLAFY_L" "$CONF"
proxlafy_load_conf "$CONF"

ask_pw() {  # var "English" "Español"
  local cur; cur="$(proxlafy_conf_get "$1" "$CONF")"
  [ -n "$cur" ] && return 0
  local pw pw2
  while :; do
    read -r -s -p "$(Ln "$2" "$3"): " pw; echo
    [ -n "$pw" ] || { warn "Cannot be empty." "No puede quedar vacía."; continue; }
    read -r -s -p "$(Ln "Repeat" "Repite"): " pw2; echo
    [ "$pw" = "$pw2" ] && break || warn "They do not match." "No coinciden."
  done
  proxlafy_set_conf "$1" "$pw" "$CONF"
}
say "Panel password (it can read, clone and emulate credentials: keep it private)" \
    "Clave del panel (puede leer, clonar y emular credenciales: mantenla privada)"
ask_pw ADMIN_PASSWORD "Panel password" "Clave del panel"
if [ -z "$(proxlafy_conf_get HOTSPOT_PASSWORD "$CONF")" ]; then
  say "Hotspot password (the WiFi the Pi creates in the field, min. 8 chars)" \
      "Clave del hotspot (la WiFi que crea la Pi en campo, mín. 8 caracteres)"
  ask_pw HOTSPOT_PASSWORD "Hotspot password" "Clave del hotspot"
fi
proxlafy_load_conf "$CONF"

STEP=0
step() { STEP=$((STEP+1)); say "[$STEP] $1" "[$STEP] ${2:-$1}"; }

step "Installing system packages" "Instalando paquetes del sistema"
"${APT[@]}" update -qq || warn "apt update had warnings" "apt update con avisos"
"${APT[@]}" install git curl python3 python3-pexpect network-manager iw avahi-daemon \
  || die "Could not install base packages." "No se pudieron instalar los paquetes base."
ok "Base packages installed." "Paquetes base instalados."

step "Proxmark3 Iceman client" "Cliente Iceman del Proxmark3"
if command -v pm3 >/dev/null 2>&1; then
  ok "pm3 already present ($(command -v pm3))." "pm3 ya está presente ($(command -v pm3))."
else
  warn "Building the Iceman client can take 15–30 min on a Zero 2 W." \
       "Compilar el cliente Iceman puede tardar 15–30 min en la Zero 2 W."
  if proxlafy_ask_yn "Build and install it now?" "¿Compilarlo e instalarlo ahora?" yes; then
    "${APT[@]}" install build-essential pkg-config libreadline-dev gcc-arm-none-eabi \
      libnewlib-arm-none-eabi libbz2-dev liblz4-dev libbluetooth-dev libpython3-dev libssl-dev qtbase5-dev \
      || warn "Some build deps failed." "Algunas dependencias de compilación fallaron."
    rm -rf /opt/proxmark3-src
    if git clone -q --depth 1 https://github.com/RfidResearchGroup/proxmark3.git /opt/proxmark3-src; then
      ( cd /opt/proxmark3-src \
        && make clean >/dev/null 2>&1; make -j"$(nproc)" client >/dev/null 2>&1 && make install >/dev/null 2>&1 ) \
        && ok "Iceman client installed." "Cliente Iceman instalado." \
        || warn "Client build failed; install pm3 manually later. The panel still runs (device shows disconnected)." \
                "Falló la compilación; instala pm3 manualmente luego. El panel igual arranca (el lector saldrá desconectado)."
    else
      warn "Could not clone the Proxmark3 repo." "No se pudo clonar el repo del Proxmark3."
    fi
  else
    warn "Skipped. Install the Iceman 'pm3' client later so the panel can talk to the reader." \
         "Omitido. Instala el cliente 'pm3' de Iceman luego para que el panel hable con el lector."
  fi
fi
# let the service user reach the Proxmark serial device · permitir el acceso al puerto serie del Proxmark
usermod -aG dialout root 2>/dev/null || true

step "Installing the Proxlafy panel" "Instalando el panel Proxlafy"
install_panel
record_rev
pause_other_project
systemctl enable proxlafy >/dev/null 2>&1
systemctl restart proxlafy
ok "Panel service enabled." "Servicio del panel activado."

step "WiFi hotspot" "Hotspot WiFi"
if command -v nmcli >/dev/null 2>&1; then
  systemctl enable NetworkManager >/dev/null 2>&1
  [ -n "$(proxlafy_conf_get WIFI_COUNTRY "$CONF")" ] && iw reg set "$(proxlafy_conf_get WIFI_COUNTRY "$CONF")" 2>/dev/null
  proxlafy_setup_hotspot && ok "Hotspot '${HOTSPOT_SSID:-Proxlafy}' ready (http://${HOTSPOT_IP:-192.168.4.1})." \
                               "Hotspot '${HOTSPOT_SSID:-Proxlafy}' listo (http://${HOTSPOT_IP:-192.168.4.1})."
  # extra known networks · redes conocidas extra
  IFS=';' read -ra NETS <<< "$(proxlafy_conf_get WIFI_NETWORKS "$CONF")"
  for n in "${NETS[@]}"; do
    [ -z "$n" ] && continue
    ssid="${n%%|*}"; pass="${n#*|}"
    nmcli connection add type wifi con-name "$ssid" ssid "$ssid" >/dev/null 2>&1
    nmcli connection modify "$ssid" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$pass" >/dev/null 2>&1
  done
  systemctl enable proxlafy-netwatch >/dev/null 2>&1
  systemctl restart proxlafy-netwatch
  ok "Network watchdog enabled." "Vigilante de red activado."
  proxlafy_harden_dns && ok "Reliable DNS set (updates won't stall on a broken router)." \
                            "DNS confiable configurado (las actualizaciones no se trabarán por un router con DNS roto)."
else
  warn "NetworkManager not available; hotspot skipped." "NetworkManager no disponible; hotspot omitido."
fi

if proxlafy_is_yes "$(proxlafy_conf_get INSTALL_TAILSCALE "$CONF")"; then
  step "Tailscale (remote access)" "Tailscale (acceso remoto)"
  command -v tailscale >/dev/null 2>&1 || curl -fsSL https://tailscale.com/install.sh | sh >/dev/null 2>&1
  key="$(proxlafy_conf_get TAILSCALE_AUTHKEY "$CONF")"
  [ -n "$key" ] && tailscale up --authkey "$key" >/dev/null 2>&1 && ok "Tailscale linked." "Tailscale enlazado." \
    || ok "Tailscale installed (link it: sudo tailscale up)." "Tailscale instalado (enlázalo: sudo tailscale up)."
fi

echo
port="$(proxlafy_conf_get PANEL_PORT "$CONF")"; port="${port:-80}"
if curl -fs -o /dev/null "http://127.0.0.1:$port/api/status"; then ok "The panel answers." "El panel responde."
else warn "The panel does not answer yet (check: proxlafy logs)." "El panel no responde todavía (revisa: proxlafy logs)."; fi

say "Done. · Listo." "Done. · Listo."
L "Open the panel:   http://${HOTSPOT_IP:-192.168.4.1}   (on the '${HOTSPOT_SSID:-Proxlafy}' hotspot)" \
  "Abre el panel:   http://${HOTSPOT_IP:-192.168.4.1}   (en el hotspot '${HOTSPOT_SSID:-Proxlafy}')"
L "Update later:     sudo proxlafy update" "Actualiza luego:   sudo proxlafy actualizar"

if [ "${PROXLAFY_NO_REBOOT:-0}" != 1 ] && [ -z "$STAGE" ]; then
  if proxlafy_ask_yn "Reboot now (recommended)?" "¿Reiniciar ahora (recomendado)?" yes; then sync; systemctl reboot; fi
fi
