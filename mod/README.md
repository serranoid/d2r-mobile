# Mod personal

Herramientas para modificar las tablas del juego sin tocar el host. No contienen nada del juego.

- `herramientas/emu.py` — emulador mínimo (unicorn) del `main` de Switch 1.0.34 para ejecutar funciones sueltas.
- `herramientas/carga_todo.py` — ejecuta emulada la carga completa de tablas en modo txt y deja los `.bin`
  compilados **por el propio código del juego**. Con `MOD=<carpeta con data/...>` compila las tablas del mod.
  Control: sobre los `.txt` vanilla tiene que dar los `.bin` vanilla (157 de 158 idénticas el 2026-11-16).
- `herramientas/inventario_txt.py` — el alijo ancho y las ranuras del mercenario del port, en `inventory.txt`.
- `herramientas/patchbin.py`, `binlayout.py` — cambiar una celda numérica de un `.bin` a mano.
- `herramientas/extrae.py` — sacar ficheros del CASC de Switch por prefijo de ruta.

Empaquetar con el mod: `DM_MOD_DIR=<carpeta con data/...>` (y `DM_TXT_TABLES=1` para el modo txt).

Las rutas de trabajo (`/mnt/trabajo/dm-work/mod/...`: imagen descomprimida del `main`, relocaciones, tablas
extraídas) están escritas a mano en los scripts.
