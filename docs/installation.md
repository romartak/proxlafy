# Installation · Instalación

Paso a paso para dejar la Raspberry lista. **EN** first, **ES** más abajo.

---

## EN — Step by step

### 0. What you need
- Raspberry Pi Zero 2 W + a microSD (8 GB+).
- Proxmark3 with **Iceman** firmware, a USB-OTG (micro-USB → USB-A) adapter, a power bank.
- A computer with **Raspberry Pi Imager** (raspberrypi.com/software).
- *(Optional)* a USB WiFi dongle for internet-while-hotspot (auto-updates in the field).

### 1. Flash the microSD
1. Open **Raspberry Pi Imager** → choose **Raspberry Pi OS Lite (64-bit)**.
2. Click the gear ⚙ (edit settings) and set:
   - **Hostname**: `proxlafy`
   - **Enable SSH** → *password authentication*
   - **Username/password** (remember them), your **home WiFi**, and your **locale/country**.
3. Write the card.

### 2. (Optional) Pre-fill the configuration
After flashing, the card shows a `bootfs` partition on your PC. You *can* drop a `proxlafy.conf`
there later, but the easiest path is to let the installer ask. Skip this step the first time.

### 3. First boot + SSH
1. Put the card in the Pi. Connect the **power bank to the PWR port**, the **Proxmark to the USB/data
   port via the OTG adapter**.
2. Wait ~60 s. From your computer on the same WiFi:
   ```sh
   ssh proxlafy@proxlafy.local        # or ssh <user>@<pi-ip>
   ```

### 4. Install (one command)
```sh
curl -fsSL https://raw.githubusercontent.com/romartak/proxlafy/main/get.sh | sudo bash
```
The installer will:
1. Install dependencies (Python, NetworkManager, git…).
2. Ask your **language**, a **panel password**, and a **hotspot password**.
3. Offer to **build the Iceman `pm3` client** (15–30 min on a Zero 2 W). Say **yes** the first time; if it
   fails or you skip it, the panel still runs — the device just shows *disconnected* until `pm3` exists.
4. Set up the WiFi hotspot, the services, and (optional) Tailscale.
5. Offer to reboot.

### 5. Connect to the panel
- **At home**: the Pi is on your WiFi — open `http://proxlafy.local` or `http://<pi-ip>`.
- **In the field**: it creates a WiFi hotspot named **`Proxlafy`** (the password you set). Join it from your
  phone and open **http://192.168.4.1**. Log in with the panel password.

### 6. Verify it works
1. **Read** tab → hold a card to the Proxmark antenna → **Read card**. It should identify the card and
   show its capabilities.
2. **Save** it (it appears in **Library**).
3. Tap it → **Emit** to emulate, **Clone to …** to write a blank, or **Recover keys & dump** for encrypted
   cards (MIFARE Classic / iCLASS).

### 7. Persistent emulation (the "leave it emitting" feature)
If you tap **Emit** and then power the kit off, the choice is **remembered**. When you power it back on, it
**resumes emulating that same card automatically** as soon as the Proxmark is detected — until you press
**Stop** in the panel. (The top banner shows *EMULATING* in green when live, or *RESUMING ON CONNECT* in
amber while it waits for the device.)

### Updating
```sh
sudo proxlafy update     # fetches, installs, health-checks the new panel, auto-rolls-back if it fails
```

### Troubleshooting
| Symptom | Fix |
|---|---|
| `proxlafy.local` not found | Use the Pi's IP (check your router), or set the hostname in Imager. |
| Panel loads, device "disconnected" | The `pm3` client is missing or the Proxmark isn't on the USB/data port. Run `pm3 -c "hw status"`. Rebuild: re-run the installer. |
| Hotspot `Proxlafy` doesn't appear | `proxlafy logs`; check `nmcli connection show proxlafy-hotspot`. The onboard WiFi can't be hotspot **and** client at once. |
| `pm3` build failed | Re-run `curl … | sudo bash`, or build it by hand from RfidResearchGroup/proxmark3, then `sudo proxlafy restart`. |
| Can't reach GitHub to update | The Pi needs internet (home WiFi or phone hotspot); on its own `Proxlafy` hotspot it can't. |

---

## ES — Paso a paso

### 0. Qué necesitas
- Raspberry Pi Zero 2 W + una microSD (8 GB o más).
- Proxmark3 con firmware **Iceman**, un adaptador USB-OTG (micro-USB → USB-A), un power bank.
- Una computadora con **Raspberry Pi Imager** (raspberrypi.com/software).
- *(Opcional)* un dongle WiFi USB para tener internet mientras es hotspot (auto-actualizar en campo).

### 1. Graba la microSD
1. Abre **Raspberry Pi Imager** → elige **Raspberry Pi OS Lite (64-bit)**.
2. Pulsa el engranaje ⚙ (editar ajustes) y configura:
   - **Hostname**: `proxlafy`
   - **Activar SSH** → *autenticación por contraseña*
   - **Usuario/contraseña** (anótalos), tu **WiFi de casa** y tu **país/locale**.
3. Graba la tarjeta.

### 2. (Opcional) Deja la configuración lista
Tras grabar, en la PC verás la partición `bootfs`. Puedes dejar ahí un `proxlafy.conf`, pero lo más fácil
es dejar que el instalador te pregunte. Salta este paso la primera vez.

### 3. Primer arranque + SSH
1. Mete la tarjeta en la Pi. Conecta el **power bank al puerto PWR** y el **Proxmark al puerto USB/datos
   con el adaptador OTG**.
2. Espera ~60 s. Desde tu computadora en la misma WiFi:
   ```sh
   ssh proxlafy@proxlafy.local        # o ssh <usuario>@<ip-de-la-pi>
   ```

### 4. Instala (un comando)
```sh
curl -fsSL https://raw.githubusercontent.com/romartak/proxlafy/main/get.sh | sudo bash
```
El instalador:
1. Instala dependencias (Python, NetworkManager, git…).
2. Te pregunta **idioma**, una **clave del panel** y una **clave del hotspot**.
3. Ofrece **compilar el cliente Iceman `pm3`** (15–30 min en la Zero 2 W). Di que **sí** la primera vez; si
   falla o lo omites, el panel igual funciona — el lector saldrá *desconectado* hasta que exista `pm3`.
4. Configura el hotspot WiFi, los servicios y (opcional) Tailscale.
5. Ofrece reiniciar.

### 5. Conéctate al panel
- **En casa**: la Pi está en tu WiFi — abre `http://proxlafy.local` o `http://<ip-de-la-pi>`.
- **En campo**: crea una WiFi llamada **`Proxlafy`** (la clave que pusiste). Conéctate desde el celular y
  abre **http://192.168.4.1**. Entra con la clave del panel.

### 6. Verifica que funciona
1. Pestaña **Leer** → acerca una tarjeta a la antena del Proxmark → **Leer tarjeta**. Debe identificarla y
   mostrar sus capacidades.
2. **Guarda** (aparece en **Biblioteca**).
3. Tócala → **Emitir** para emular, **Clonar a …** para escribir un blanco, o **Recuperar claves y volcar**
   para tarjetas cifradas (MIFARE Classic / iCLASS).

### 7. Emulación persistente (lo de "déjala emitiendo")
Si pulsas **Emitir** y luego apagas el equipo, la elección **se recuerda**. Al reencenderlo, **vuelve a
emular esa misma tarjeta automáticamente** en cuanto detecta el Proxmark — hasta que pulses **Detener** en
el panel. (El banner de arriba muestra *EMULANDO* en verde cuando está activo, o *REANUDANDO AL CONECTAR*
en ámbar mientras espera el lector.)

### Actualizar
```sh
sudo proxlafy actualizar   # trae, instala, comprueba el panel nuevo y vuelve solo si falla
```

### Problemas frecuentes
| Síntoma | Solución |
|---|---|
| No encuentra `proxlafy.local` | Usa la IP de la Pi (mírala en el router), o fija el hostname en Imager. |
| El panel carga, lector "desconectado" | Falta el cliente `pm3` o el Proxmark no está en el puerto USB/datos. Prueba `pm3 -c "hw status"`. Recompila: reejecuta el instalador. |
| No aparece el hotspot `Proxlafy` | `proxlafy registro`; revisa `nmcli connection show proxlafy-hotspot`. El WiFi interno no puede ser hotspot **y** cliente a la vez. |
| Falló la compilación de `pm3` | Reejecuta `curl … | sudo bash`, o compílalo a mano desde RfidResearchGroup/proxmark3 y luego `sudo proxlafy restart`. |
| No llega a GitHub para actualizar | La Pi necesita internet (WiFi de casa o hotspot del celular); en su propio hotspot `Proxlafy` no puede. |
