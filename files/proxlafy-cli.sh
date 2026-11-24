#!/bin/bash
# =====================================================================
#  proxlafy · command-line tool · herramienta de línea de comandos
#  Installed as /usr/local/bin/proxlafy · Se instala como /usr/local/bin/proxlafy
#
#    proxlafy status        device and service state · estado del lector y del servicio
#    proxlafy logs          live journal · registro en vivo
#    proxlafy update        update from GitHub (auto-rollback) · actualizar (auto-rollback)
#    proxlafy rollback      previous version · versión anterior
#    proxlafy restart       restart the panel · reiniciar el panel
#    proxlafy hotspot       force the hotspot (auto releases it) · forzar hotspot (auto lo libera)
#    proxlafy switch        switch to the other lab project (SDR-Kit) · cambiar al otro proyecto (SDR-Kit)
#    proxlafy labs          list installed lab projects · listar proyectos instalados
#    proxlafy config        edit proxlafy.conf · editar la configuración
#    proxlafy version       installed version · versión instalada
#  Spanish aliases work too · Los alias en español también funcionan.
# =====================================================================
set -o pipefail
OPT=/opt/proxlafy
CONF=/etc/proxlafy/proxlafy.conf
# shellcheck source=proxlafy-lib.sh
source "$OPT/proxlafy-lib.sh" 2>/dev/null || source /opt/proxlafy/proxlafy-lib.sh
proxlafy_load_conf "$CONF"
proxlafy_lang_init

need_root() { [ "$(id -u)" -eq 0 ] || { L "Use sudo: sudo proxlafy $1" "Usa sudo: sudo proxlafy $1"; exit 1; }; }

cmd="${1:-status}"; shift 2>/dev/null
case "$cmd" in
  status|estado)
    echo "── Proxlafy $(cat "$OPT/VERSION" 2>/dev/null) ──"
    systemctl is-active --quiet proxlafy && L "Panel: running" "Panel: activo" || L "Panel: stopped" "Panel: detenido"
    port="${PANEL_PORT:-80}"
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:$port/api/status" 2>/dev/null)"
    [ "$code" = "200" ] && L "API: OK (http://127.0.0.1:$port)" "API: OK (http://127.0.0.1:$port)" || L "API: no answer ($code)" "API: sin respuesta ($code)"
    ip="$(nmcli -g IP4.ADDRESS device show 2>/dev/null | head -1 | cut -d/ -f1)"
    [ -n "$ip" ] && L "Address: http://$ip" "Dirección: http://$ip"
    ;;
  logs|registro|log)
    journalctl -u proxlafy -u proxlafy-netwatch -f -n 60 --no-hostname
    ;;
  update|actualizar|up)
    need_root "update"; exec bash "$OPT/proxlafy-update.sh" "$@"
    ;;
  rollback|volver)
    need_root "rollback"; exec bash "$OPT/proxlafy-update.sh" --rollback
    ;;
  restart|reiniciar)
    need_root "restart"; systemctl restart proxlafy && L "Panel restarted." "Panel reiniciado."
    ;;
  start|iniciar)  need_root "start"; systemctl start proxlafy ;;
  stop|detener)   need_root "stop"; systemctl stop proxlafy ;;
  hotspot)
    need_root "hotspot"; mkdir -p /run/proxlafy
    if [ "${1:-}" = "auto" ]; then echo auto > /run/proxlafy/netmode; L "Hotspot released (auto)." "Hotspot liberado (auto)."
    else echo hotspot > /run/proxlafy/netmode; L "Hotspot forced." "Hotspot forzado."; systemctl restart proxlafy-netwatch; fi
    ;;
  config|configurar)
    need_root "config"; "${EDITOR:-nano}" "$CONF"
    L "Apply changes: sudo proxlafy restart" "Aplica los cambios: sudo proxlafy restart"
    ;;
  viewer|lector)
    need_root "viewer"
    read -r -s -p "$(Ln "Read-only password (empty = off): " "Clave de solo lectura (vacía = desactivar): ")" pw; echo
    proxlafy_set_conf VIEWER_PASSWORD "$pw" "$CONF"; systemctl restart proxlafy
    L "Done." "Listo."
    ;;
  switch|cambiar)
    need_root "switch"
    if [ -x /usr/local/sbin/labswitch ]; then exec /usr/local/sbin/labswitch "${1:-other}"
    else L "labswitch not installed." "labswitch no está instalado."; exit 1; fi
    ;;
  labs|proyectos)
    [ -x /usr/local/sbin/labswitch ] && exec /usr/local/sbin/labswitch status || { L "labswitch not installed." "labswitch no está instalado."; exit 1; }
    ;;
  version|versión|-v|--version)
    echo "proxlafy $(cat "$OPT/VERSION" 2>/dev/null || echo '?')"
    repo="${PROXLAFY_REPO:-$(git -C /opt/proxlafy-src remote get-url origin 2>/dev/null)}"
    echo "repo: ${repo:-$PROXLAFY_DEFAULT_REPO}  ·  branch: ${PROXLAFY_BRANCH:-main}"
    ;;
  help|ayuda|-h|--help)
    sed -n '3,16p' "$OPT/proxlafy-cli.sh" | sed 's/^#\s\?//'
    ;;
  *)
    L "Unknown command: $cmd  (try: proxlafy help)" "Comando desconocido: $cmd  (prueba: proxlafy ayuda)"; exit 1
    ;;
esac
