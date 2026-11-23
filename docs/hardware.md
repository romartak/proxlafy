# Hardware · Hardware

> **EN** below · **ES** más abajo.

## EN

### Parts
- **Raspberry Pi Zero 2 W** — quad-core, 512 MB RAM, onboard 2.4 GHz WiFi.
- **Proxmark3 with Iceman firmware** — any variant (RDV4, PM3 Easy / generic). LF + HF antennas.
- **Power bank** + a short cable to the Pi's **PWR** port.
- **USB OTG adapter** (micro-USB → USB-A) for the Proxmark on the Pi's **USB/data** port.
- *(Optional)* a **USB WiFi dongle** to keep internet while the onboard WiFi is the hotspot.
- **Blank T5577 cards** for LF writes; *magic* / gen1a cards for HF where supported.

### Wiring
The Zero 2 W has **two micro-USB ports**:

```
Power bank ─────────────► [PWR]  Raspberry Pi Zero 2 W  [USB] ──OTG──► Proxmark3 ──► antenna
                                         │
                                         └─(onboard WiFi = hotspot "Proxlafy")
            USB WiFi dongle (optional) ──┘  = internet client, for auto-update
```

- Power goes to **PWR**; the Proxmark goes to **USB/data**. Don't swap them.
- The onboard WiFi becomes the **hotspot** so you reach the panel in the field. A second (USB) WiFi is only
  needed if you also want internet for `proxlafy update` at the same time.

### Firmware check
Proxlafy assumes the **Iceman** firmware (command syntax like `lf hid`, `hf mf`, `hf iclass`). Confirm:

```sh
pm3 -c "hw version"     # should mention "Iceman"
```

If you have the official/stock firmware, set `PM3_FIRMWARE="official"` in `proxlafy.conf`; some command
syntaxes differ and may need adjusting in `files/pm3.py`.

### Note on HID Prox vs MIFARE
HID **Prox** is **125 kHz (LF)**; MIFARE and HID **iCLASS** are **13.56 MHz (HF)** — different radios. You
cannot clone an HID Prox onto a MIFARE card. To clone HID Prox, write to a **T5577** (125 kHz) blank.

---

## ES

### Piezas
- **Raspberry Pi Zero 2 W** — cuatro núcleos, 512 MB RAM, WiFi 2.4 GHz integrado.
- **Proxmark3 con firmware Iceman** — cualquier variante (RDV4, PM3 Easy / genérico). Antenas LF + HF.
- **Power bank** + un cable corto al puerto **PWR** de la Pi.
- **Adaptador USB OTG** (micro-USB → USB-A) para el Proxmark en el puerto **USB/datos** de la Pi.
- *(Opcional)* un **dongle WiFi USB** para tener internet mientras el WiFi interno es el hotspot.
- **Tarjetas T5577** en blanco para escrituras LF; tarjetas *magic* / gen1a para HF donde se soporte.

### Conexionado
La Zero 2 W tiene **dos micro-USB**:

```
Power bank ─────────────► [PWR]  Raspberry Pi Zero 2 W  [USB] ──OTG──► Proxmark3 ──► antena
                                         │
                                         └─(WiFi interno = hotspot "Proxlafy")
         Dongle WiFi USB (opcional) ─────┘  = cliente a internet, para auto-actualizar
```

- La energía va al **PWR**; el Proxmark al **USB/datos**. No los intercambies.
- El WiFi interno queda como **hotspot** para llegar al panel en campo. El segundo WiFi (USB) solo hace
  falta si además quieres internet para `proxlafy actualizar` al mismo tiempo.

### Comprobar el firmware
Proxlafy asume firmware **Iceman** (sintaxis `lf hid`, `hf mf`, `hf iclass`). Confírmalo:

```sh
pm3 -c "hw version"     # debe mencionar "Iceman"
```

Si tienes el firmware oficial, pon `PM3_FIRMWARE="official"` en `proxlafy.conf`; algunas sintaxis cambian
y puede que haya que ajustarlas en `files/pm3.py`.

### Nota HID Prox vs MIFARE
HID **Prox** es **125 kHz (LF)**; MIFARE y HID **iCLASS** son **13.56 MHz (HF)** — radios distintas. No se
puede clonar una HID Prox en una MIFARE. Para clonar HID Prox, escribe en una **T5577** (125 kHz) en blanco.
