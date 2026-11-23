<div align="center">

# Proxlafy

**Un banco de trabajo RFID de bolsillo — Raspberry Pi Zero 2 W + Proxmark3 (Iceman) + power bank, manejado desde el celular.**

Lee, cataloga, clona y emula tarjetas LF (125 kHz) y HF (13.56 MHz) desde un panel web sin internet,
con hotspot WiFi automático y actualizaciones con auto-rollback.

[🇬🇧 Read in English](README.md) · [Hardware](docs/hardware.md) · [Actualizaciones](docs/updating.md)

</div>

> [!IMPORTANT]
> **Solo uso autorizado.** Proxlafy es para un laboratorio privado: tus propias tarjetas y lectores, o
> trabajos con permiso explícito por escrito (pentesting, investigación, formación). Usarlo contra
> sistemas de acceso que no son tuyos o que no estás autorizado a probar es ilegal. Tú eres responsable
> del uso que le des.

---

## Qué hace

- **Leer e identificar** una tarjeta en la antena (LF, HF o auto) entre **29 familias** — ver abajo.
- **Decodificar** — con tarjetas cifradas el panel te lo avisa y puede **recuperar claves y volcar** (MIFARE
  Classic `autopwn`, iCLASS, Ultralight), desde la hoja de detalle de la tarjeta.
- **Capacidades de un vistazo** — cada tarjeta muestra chips: *emulable*, *clonable → a qué blanco*, *cifrada*.
- **Biblioteca** — guarda cada lectura con nombre y notas; queda en la Pi y sobrevive a las actualizaciones. Búsqueda + filtro LF/HF.
- **Emular** — tocas una tarjeta y el Proxmark la emula; un banner muestra cuál está activa, se detiene con un toque.
- **Emulación persistente** — emites una tarjeta, apagas el equipo, y al **reencender vuelve a emitirla sola**
  automáticamente, hasta que la canceles en el panel.
- **Escribir / clonar** — escribe una credencial guardada al blanco correcto (T5577 para LF, magic para HF).
- **Desde el celular** — panel sin internet por el hotspot WiFi de la Pi; nada sale del dispositivo.

Ver **[docs/installation.md](docs/installation.md)** para la guía completa (de grabar la SD a la primera lectura).

> [!NOTE]
> **¿Aún sin hardware?** Corre el panel en modo demo en cualquier computadora:
> `PROXLAFY_DEMO=1 python3 files/proxlafy_server.py --port 8080` → http://localhost:8080

## Familias de tarjetas soportadas

**LF 125 kHz** — HID Prox, EM410x, Indala, AWID, ioProx (Kantech), Paradox, Pyramid (Farpointe), Viking,
Noralsy, Jablotron, Keri, Nexwatch (Honeywell), Securakey, Gallagher, Presco, FDX-B (animal), Visa2000,
EM4x05/4x50, T55x7.

**HF 13.56 MHz** — MIFARE Classic 1K/4K, MIFARE Ultralight / NTAG, MIFARE DESFire, MIFARE Plus, HID iCLASS,
ISO15693 / iCODE, FeliCa, Topaz, LEGIC, ISO14443-B (SRx).

Los formatos abiertos son clonables/emulables; los cifrados (DESFire SL3, iCLASS Elite, Plus SL3…) se
identifican y se leen hasta donde su cripto lo permite — el panel es honesto sobre qué se puede y qué no.

## Hardware

| Pieza | Notas |
|---|---|
| Raspberry Pi Zero 2 W | WiFi integrado (se usa como hotspot) |
| Proxmark3 (firmware Iceman) | Al micro-USB de **datos (USB)** de la Pi, con un adaptador OTG |
| Power bank | Al micro-USB de **energía (PWR)** de la Pi (separado del de datos) |
| Dongle WiFi USB | *Opcional* — como cliente a internet, para que la Pi se auto-actualice mientras el WiFi interno sigue de hotspot |
| Tarjetas **T5577** en blanco | Para escribir clones LF |

Ver [docs/hardware.md](docs/hardware.md) para el conexionado y la comprobación del firmware.

## Instalación

En la Pi, por SSH, un solo comando:

```sh
curl -fsSL https://raw.githubusercontent.com/romartak/proxlafy/main/get.sh | sudo bash
```

Instala las dependencias, ofrece compilar el cliente Iceman `pm3`, configura el hotspot WiFi y los
servicios, y te pide una clave para el panel. Luego abre **http://192.168.4.1** en el hotspot `Proxlafy`.

Puedes dejar las respuestas listas editando [`proxlafy.conf`](proxlafy.conf) antes (también desde la PC,
en la partición `bootfs` de la microSD).

## El comando `proxlafy`

```sh
proxlafy estado         # estado del lector y del servicio
proxlafy registro       # registro en vivo
sudo proxlafy actualizar # actualizar desde GitHub (comprueba el panel; si falla, vuelve solo)
sudo proxlafy volver
sudo proxlafy hotspot   # forzar el hotspot ("auto" lo libera)
sudo proxlafy configurar # editar proxlafy.conf
```
Los nombres en inglés también funcionan (`update`, `rollback`, `status`, `config`).

## Actualizaciones que no te dejan tirado

`sudo proxlafy actualizar` trae el último commit, conserva tu configuración y tu biblioteca, instala y
luego consulta `/api/status`. Si el panel nuevo no responde en ~60 s, **restaura la versión anterior
automáticamente**. Detalles en [docs/updating.md](docs/updating.md).

## Cómo funciona

- **Panel** — `files/proxlafy_server.py`: Python puro de la biblioteca estándar (`http.server`), sirve el
  panel sin internet de `files/web/` y una API JSON pequeña. Ligero para la Zero 2 W.
- **Lector** — `files/pm3.py`: mantiene una sesión del cliente Iceman `pm3` viva (con `pexpect`) y
  serializa cada comando al lector. Un backend demo deja usar la interfaz sin hardware.
- **Red** — `files/proxlafy-netwatch.sh`: al arrancar se conecta a una WiFi conocida; si no, levanta su
  propio hotspot, y mantiene la Pi accesible de cualquier forma (NetworkManager).
- **Actualizaciones** — `files/proxlafy-update.sh`: basadas en commits, con health-check y auto-rollback.

## Licencia

MIT — ver [LICENSE](LICENSE).
