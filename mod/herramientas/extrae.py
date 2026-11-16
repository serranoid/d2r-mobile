#!/usr/bin/env python3
"""Extrae ficheros del CASC de Switch a un directorio, por prefijo de ruta lógica.
uso: extrae.py <RomFS> <salida> <prefijo> [<prefijo>...]"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path.home() / 'ia/d2r-mobile/dm/tools'))
import casc_overlay as co
src, out, pref = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), [p.lower() for p in sys.argv[3:]]
man = co.read_manifest(src); n = 0
for path, f in man.items():
    if not any(path.lower().startswith(p) for p in pref): continue
    ek = bytes.fromhex(f[6]); fn = src / 'data' / f'{ek[9]:02d}-{ek[10]:08d}.data'
    with fn.open('rb') as st:
        st.seek(int.from_bytes(ek[11:16], 'big')); raw = st.read(int(f[7]))
    if raw[:4] == b'BLTE': data = co.read_data_file(src / 'data', ek, int(f[7]))
    elif f[8] == 'n': data = raw
    else:
        import zlib; data = zlib.decompress(raw)
    assert len(data) == int(f[5]), path
    dst = out / path.split(':', 1)[-1]; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data); n += 1
print(n, 'ficheros')
