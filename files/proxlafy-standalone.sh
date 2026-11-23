#!/bin/bash
# =====================================================================
#  Proxlafy · program a Proxmark3 standalone mode · programar un modo standalone
#  Builds an Iceman firmware image with the chosen STANDALONE mode and flashes it.
#  The normal client/USB keeps working; a long button-press enters the mode.
#  Compila una imagen Iceman con el modo STANDALONE elegido y la graba.
#  El cliente/USB normal sigue funcionando; una pulsación larga entra al modo.
#
#    proxlafy-standalone.sh LF_SAMYRUN
#
#  Takes ~15–30 min on a Zero 2 W. Do NOT unplug the Proxmark during flashing.
#  Tarda ~15–30 min en una Zero 2 W. NO desconectes el Proxmark durante la grabación.
# =====================================================================
set -o pipefail
MODE="${1:?mode required · falta el modo}"
SRC="${PROXMARK_SRC:-/opt/proxmark3-src}"

echo "==> Standalone: $MODE"
[ -d "$SRC/.git" ] || { echo "✖ No Proxmark source at $SRC. Run the installer and build pm3 first."; exit 1; }
cd "$SRC" || exit 1

# 1) select the standalone mode in Makefile.platform
PLAT="$SRC/Makefile.platform"
[ -f "$PLAT" ] || cp "$SRC/Makefile.platform.sample" "$PLAT" 2>/dev/null || { echo "STANDALONE=$MODE" > "$PLAT"; }
if grep -qE '^[#[:space:]]*STANDALONE=' "$PLAT"; then
  sed -i -E "s|^[#[:space:]]*STANDALONE=.*|STANDALONE=$MODE|" "$PLAT"
else
  echo "STANDALONE=$MODE" >> "$PLAT"
fi
echo "==> Makefile.platform: $(grep -E '^STANDALONE=' "$PLAT")"

# 2) build
echo "==> make clean && make (this is the slow part)…"
make clean >/dev/null 2>&1
if ! make -j"$(nproc)" 2>&1 | tail -20; then
  echo "✖ Build failed · Falló la compilación"; exit 1
fi

# 3) flash the full image (bootloader + fullimage)
echo "==> Flashing… do NOT unplug · Grabando… NO desconectes"
if [ -x "$SRC/pm3-flash-all" ]; then
  "$SRC/pm3-flash-all" 2>&1 | tail -25
elif command -v pm3-flash-all >/dev/null 2>&1; then
  pm3-flash-all 2>&1 | tail -25
else
  ./client/proxmark3 "$(ls /dev/ttyACM* 2>/dev/null | head -1)" --flash --image armsrc/obj/fullimage.elf 2>&1 | tail -25
fi
rc=$?
[ $rc -eq 0 ] && echo "✔ Done. Standalone mode '$MODE' flashed. Long-press the button to enter it." \
              || echo "✖ Flash failed (rc=$rc). Check the USB/bootloader and try again."
exit $rc
