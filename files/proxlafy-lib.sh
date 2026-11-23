#!/bin/bash
# Proxlafy · shared functions (used by the installer, the network watchdog and the proxlafy command)
# Proxlafy · funciones compartidas (las usan el instalador, el vigilante de red y el comando proxlafy)

# Reads KEY="value" without running anything: a quoted value is taken literally (a $ in a password is safe).
# Lee KEY="valor" sin ejecutar nada: el valor entre comillas se toma literal (un $ en una clave no se rompe).
proxlafy_load_conf() {
  local f="${1:-/etc/proxlafy/proxlafy.conf}" line key val
  local re_kv='^[[:space:]]*(export[[:space:]]+)?([A-Z_][A-Z0-9_]*)=(.*)$'
  local re_dq='^"([^"]*)"[[:space:]]*(#.*)?$'
  local re_sq="^'([^']*)'[[:space:]]*(#.*)?\$"
  [ -r "$f" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    [[ $line =~ $re_kv ]] || continue
    key="${BASH_REMATCH[2]}"
    val="${BASH_REMATCH[3]}"
    if [[ $val =~ $re_dq ]] || [[ $val =~ $re_sq ]]; then
      val="${BASH_REMATCH[1]}"
    else
      val="${val%%#*}"
      val="${val#"${val%%[![:space:]]*}"}"
      val="${val%"${val##*[![:space:]]}"}"
    fi
    printf -v "$key" '%s' "$val"
  done < "$f"
}

# Changes (or adds) KEY="value" in the configuration file. · Cambia (o agrega) KEY="valor" en la configuración.
proxlafy_set_conf() {
  local key="$1" val="$2" f="${3:-/etc/proxlafy/proxlafy.conf}" tmp
  tmp="$(mktemp)"
  if grep -qE "^[[:space:]]*${key}=" "$f" 2>/dev/null; then
    K="$key" V="$val" awk 'BEGIN{d=0} !d && $0 ~ "^[[:space:]]*" ENVIRON["K"] "=" {print ENVIRON["K"] "=\"" ENVIRON["V"] "\""; d=1; next} {print}' "$f" > "$tmp"
  else
    { [ -s "$f" ] && sed -e '$a\' "$f"; printf '%s="%s"\n' "$key" "$val"; } > "$tmp"
  fi
  cat "$tmp" > "$f"
  rm -f "$tmp"
}

# Adds to config $2 the keys of template $1 it does not have yet (never changes your values). Prints how many.
# Agrega a la configuración $2 las claves de la plantilla $1 que todavía no tenga (nunca cambia tus valores).
proxlafy_merge_conf() {
  local tpl="$1" dst="$2" added=0 line key
  [ -r "$tpl" ] && [ -f "$dst" ] || { echo 0; return 0; }
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    [[ $line =~ ^([A-Z_][A-Z0-9_]*)= ]] || continue
    key="${BASH_REMATCH[1]}"
    grep -qE "^[[:space:]]*${key}=" "$dst" && continue
    [ "$key" = PROXLAFY_LANG ] && line="${line/#PROXLAFY_LANG=\"\"/PROXLAFY_LANG=\"es\"}"
    [ $added -eq 0 ] && printf '\n# --- New options added by an update · Opciones nuevas agregadas por una actualización (%s) ---\n' "$(date +%F)" >> "$dst"
    printf '%s\n' "$line" >> "$dst"
    added=$((added + 1))
  done < "$tpl"
  echo "$added"
}

# GitHub repository used to install and update (PROXLAFY_REPO in proxlafy.conf overrides it)
# Repositorio de GitHub de donde se instala y actualiza (se puede cambiar con PROXLAFY_REPO en proxlafy.conf)
export PROXLAFY_DEFAULT_REPO="https://github.com/romartak/proxlafy.git"

# Creates or updates the NetworkManager hotspot connection (does not bring it up or down).
# Crea o actualiza la conexión hotspot de NetworkManager (no la activa ni la corta si ya está activa).
proxlafy_setup_hotspot() {
  local con="${HOTSPOT_CON:-proxlafy-hotspot}" iface="${WIFI_IFACE:-wlan0}"
  local ip="${HOTSPOT_IP:-192.168.4.1}" ch="${HOTSPOT_CHANNEL:-6}"
  local props=(connection.autoconnect no 802-11-wireless.ssid "${HOTSPOT_SSID:-Proxlafy}"
    802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel "$ch"
    ipv4.method shared ipv4.addresses "$ip/24" ipv6.method disabled
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASSWORD"
    wifi-sec.proto rsn wifi-sec.pairwise ccmp wifi-sec.group ccmp wifi-sec.pmf disable)
  if nmcli -t -f NAME connection show | grep -Fxq -- "$con"; then
    nmcli connection modify "$con" "${props[@]}"
  else
    nmcli connection add type wifi ifname "$iface" con-name "$con" ssid "${HOTSPOT_SSID:-Proxlafy}" "${props[@]}" >/dev/null
  fi
}

# ---------------------------------------------------------------------
#  Language · Idioma  (en | es)
#  Order: env PROXLAFY_LANG → proxlafy.conf → system language ($LANG: es* → es) → en
# ---------------------------------------------------------------------
PROXLAFY_LANG_ENV="${PROXLAFY_LANG_ENV-${PROXLAFY_LANG:-}}"
PROXLAFY_L=""

proxlafy_norm_lang() {
  case "${1:-}" in
    [Ee][Ss]*|[Ss][Pp]*) echo es ;;
    [Ee][Nn]*|[Ii][Nn][Gg]*) echo en ;;
  esac
}

proxlafy_sys_lang() {
  local v
  for v in "${LC_ALL:-}" "${LC_MESSAGES:-}" "${LANG:-}"; do
    case "$v" in ''|C|C.*|POSIX) continue ;; esac
    case "$v" in [Ee][Ss]*) echo es ;; *) echo en ;; esac
    return 0
  done
  echo en
}

proxlafy_conf_get() { ( unset "$1"; proxlafy_load_conf "$2"; printf '%s\n' "${!1:-}" ); }

proxlafy_conf_lang() {
  [ -r "$1" ] || return 0
  if grep -qE '^[[:space:]]*(export[[:space:]]+)?PROXLAFY_LANG=' "$1"; then
    proxlafy_norm_lang "$(proxlafy_conf_get PROXLAFY_LANG "$1")"
  else
    echo es
  fi
}

proxlafy_lang_init() {
  local l
  l="$(proxlafy_norm_lang "$PROXLAFY_LANG_ENV")"
  if [ -n "$l" ]; then PROXLAFY_LANG="$PROXLAFY_LANG_ENV"; else l="$(proxlafy_norm_lang "${PROXLAFY_LANG:-}")"; fi
  [ -n "$l" ] || l="$(proxlafy_sys_lang)"
  PROXLAFY_L="$l"
}

# proxlafy_pick "English" "Español" → REPLY (no subshell). With one argument, that text in any language.
proxlafy_pick() {
  [ -n "$PROXLAFY_L" ] || proxlafy_lang_init
  if [ "$PROXLAFY_L" = es ] && [ $# -ge 2 ]; then REPLY="$2"; else REPLY="${1:-}"; fi
}
# L "English" "Español": prints the text in the active language, as is (% and \ are safe)
L()  { proxlafy_pick "$@"; printf '%s\n' "$REPLY"; }
Ln() { proxlafy_pick "$@"; printf '%s' "$REPLY"; }

proxlafy_is_yes() {
  case "${1,,}" in y|yes|s|si|sí|sÍ|true|1|on) return 0 ;; *) return 1 ;; esac
}

# proxlafy_ask_yn "Question?" "¿Pregunta?" yes|no  → 0 = yes.
proxlafy_ask_yn() {
  local def="${3:-no}" hint ans
  if proxlafy_is_yes "$def"; then def=yes; hint="$(L "(yes/no) [yes]" "(si/no) [si]")"
  else def=no; hint="$(L "(yes/no) [no]" "(si/no) [no]")"; fi
  read -r -p "$(Ln "$1" "$2") $hint: " ans || ans=""
  ans="${ans#"${ans%%[![:space:]]*}"}"; ans="${ans%"${ans##*[![:space:]]}"}"
  [ -n "$ans" ] || ans="$def"
  proxlafy_is_yes "$ans"
}

# One text or "English" "Español" · un texto o "English" "Español"
proxlafy_pick_say() { proxlafy_pick "$@"; }
