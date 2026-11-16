#!/usr/bin/env python3
"""Cambia valores numéricos en una tabla .bin localizando fila y columna a partir del .txt vanilla.
uso: patchbin.py <vanilla_excel_dir> <salida_dir> <tabla> <col_clave>=<valor_clave> <col>=<nuevo> [<col>=<nuevo>...]
Escribe <salida_dir>/<tabla>.bin; comprueba antes que el .bin vanilla contiene el valor del .txt en ese sitio."""
import sys, struct, os
sys.path.insert(0, os.path.dirname(__file__)); import binlayout
src, dst, tab = sys.argv[1:4]; kc, kv = sys.argv[4].split('=', 1); sets = dict(a.split('=', 1) for a in sys.argv[5:])
txt, binf = os.path.join(src, tab + '.txt'), os.path.join(src, tab + '.bin')
hdr, rows, b, n, rs = binlayout.load(txt, binf); assert len(rows) == n, 'filas txt != filas bin'
lay = binlayout.infer(hdr, rows, b, n, rs, set(sets))
ri = [i for i, r in enumerate(rows) if r[hdr.index(kc)] == kv]; assert len(ri) == 1, f'{kc}={kv}: {len(ri)} filas'
b = bytearray(b)
for c, v in sets.items():
    assert c in lay and lay[c][3] == 1, f'columna {c} no localizada de forma única'
    off, w, f, _ = lay[c]; pos = 4 + ri[0] * rs + off; old = struct.unpack_from(f, b, pos)[0]
    assert old == int(rows[ri[0]][hdr.index(c)] or 0), 'el bin no contiene el valor del txt'
    struct.pack_into(f, b, pos, int(v)); print(f'{tab}[{kv}].{c}: {old} -> {v} (offset fichero {pos:#x})')
os.makedirs(dst, exist_ok=True); open(os.path.join(dst, tab + '.bin'), 'wb').write(b)
