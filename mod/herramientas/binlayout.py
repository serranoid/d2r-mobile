#!/usr/bin/env python3
"""Infiere, comparando un .txt con su .bin, en qué offset y con qué ancho guarda el .bin cada columna numérica.
uso: binlayout.py <tabla.txt> <tabla.bin> [columna...]   → imprime nfilas, tamaño de registro y offset por columna"""
import sys, struct
def load(txt, binf):
    rows = [l.rstrip('\r\n').split('\t') for l in open(txt, encoding='latin1')]
    hdr, rows = rows[0], [r for r in rows[1:] if r and r[0] != 'Expansion']
    b = open(binf, 'rb').read(); n = struct.unpack_from('<I', b, 0)[0]
    return hdr, rows, b, n, (len(b) - 4) // n if n else 0
def infer(hdr, rows, b, n, rs, cols=None):
    out = {}
    if len(rows) != n: return None
    for ci, c in enumerate(hdr):
        if cols and c not in cols: continue
        try: vals = [int(r[ci]) if ci < len(r) and r[ci] != '' else 0 for r in rows]
        except ValueError: continue
        if len(set(vals)) < 2: continue
        for w, f in ((4, '<i'), (2, '<h'), (1, '<b'), (4, '<I'), (2, '<H'), (1, '<B')):
            hit = [o for o in range(0, rs - w + 1) if all(struct.unpack_from(f, b, 4 + i * rs + o)[0] == v for i, v in enumerate(vals))]
            if hit: out[c] = (hit[0], w, f, len(hit)); break
    return out
if __name__ == '__main__':
    hdr, rows, b, n, rs = load(sys.argv[1], sys.argv[2])
    print('filas txt', len(rows), 'filas bin', n, 'registro', rs, 'resto', (len(b) - 4) - n * rs)
    lay = infer(hdr, rows, b, n, rs, set(sys.argv[3:]) or None)
    if lay is None: print('NO CUADRA el número de filas'); sys.exit(1)
    num = 0
    for c in hdr:
        if c in lay: num += 1; print(f'  {c}: +{lay[c][0]} ancho {lay[c][1]}' + (f' (ambiguo, {lay[c][3]} candidatos)' if lay[c][3] > 1 else ''))
    print('columnas numéricas localizadas:', num, 'de', len(hdr))
