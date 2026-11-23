# Updating · Actualizaciones

## EN

Proxlafy updates itself from GitHub, keeps your configuration and your card library, checks that the new
version starts and **rolls back automatically** if it does not.

### From the command line
```sh
sudo proxlafy update          # show the changes and ask before installing
proxlafy update --check       # only report whether there is something new
sudo proxlafy update --yes    # install without asking
sudo proxlafy update --force  # reinstall even if already up to date
proxlafy version              # installed version, commit, repo and branch
```
Spanish names work too (`actualizar`, `--buscar`, `--si`, `--forzar`, `volver`).

### What is preserved
| Kept | Where |
|---|---|
| Your configuration | `/etc/proxlafy/proxlafy.conf` — new options are **appended** under a dated comment; existing values are never changed. A pre-update copy is saved as `proxlafy.conf.antes-de-actualizar` |
| Your card library | `/var/lib/proxlafy/cards/` |

### How it works
1. Check internet (`github.com`) and fetch `PROXLAFY_BRANCH` from `PROXLAFY_REPO` into `/opt/proxlafy-src`.
2. If there is a new commit, back up `/opt/proxlafy` → `/opt/proxlafy.prev` and remember the commit.
3. Install (quick: copy the panel; full: run `install.sh` when `INSTALL_REV` increased, ending in a reboot).
4. Poll `http://127.0.0.1:<PANEL_PORT>/api/status`. A `200`/`401` within ~60 s = healthy → record the commit.
5. Otherwise restore `/opt/proxlafy.prev`, reset the source, restart the panel and report the rollback.

Only one update runs at a time (`/run/proxlafy-update.lock`). Logs: `/var/log/proxlafy-update.log`.

### Manual rollback
```sh
sudo proxlafy rollback   # swaps /opt/proxlafy with /opt/proxlafy.prev; run it again to go forward
```

### Testing a branch
Push to e.g. `pruebas`, set `PROXLAFY_BRANCH="pruebas"` with `sudo proxlafy config`, then
`sudo proxlafy update`. Clear it (empty = `main`) to return to stable.

---

## ES

Proxlafy se actualiza desde GitHub, conserva tu configuración y tu biblioteca de tarjetas, comprueba que
la versión nueva arranca y **vuelve sola a la anterior** si no lo hace.

### Desde la línea de comandos
```sh
sudo proxlafy actualizar          # muestra los cambios y pregunta antes de instalar
proxlafy actualizar --buscar      # solo dice si hay algo nuevo
sudo proxlafy actualizar --si     # instala sin preguntar
sudo proxlafy actualizar --forzar # reinstala aunque esté al día
proxlafy version                  # versión instalada, commit, repo y rama
```

### Qué se conserva
| Se mantiene | Dónde |
|---|---|
| Tu configuración | `/etc/proxlafy/proxlafy.conf` — las opciones nuevas se **agregan** bajo un comentario con fecha; tus valores no se tocan. Se guarda una copia previa como `proxlafy.conf.antes-de-actualizar` |
| Tu biblioteca | `/var/lib/proxlafy/cards/` |

### Cómo funciona
1. Comprueba internet (`github.com`) y trae `PROXLAFY_BRANCH` de `PROXLAFY_REPO` a `/opt/proxlafy-src`.
2. Si hay un commit nuevo, respalda `/opt/proxlafy` → `/opt/proxlafy.prev` y recuerda el commit.
3. Instala (rápida: copia el panel; completa: ejecuta `install.sh` si subió `INSTALL_REV`, y reinicia).
4. Consulta `http://127.0.0.1:<PANEL_PORT>/api/status`. Un `200`/`401` en ~60 s = sano → anota el commit.
5. Si no, restaura `/opt/proxlafy.prev`, reinicia el panel e informa del rollback.

Solo corre una actualización a la vez (`/run/proxlafy-update.lock`). Registro: `/var/log/proxlafy-update.log`.

### Rollback manual
```sh
sudo proxlafy volver   # intercambia /opt/proxlafy con /opt/proxlafy.prev; repítelo para ir hacia adelante
```

### Probar una rama
Sube a, por ejemplo, `pruebas`, pon `PROXLAFY_BRANCH="pruebas"` con `sudo proxlafy configurar` y luego
`sudo proxlafy actualizar`. Déjalo vacío (`main`) para volver a la estable.
