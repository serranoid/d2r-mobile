#!/usr/bin/env python3
"""Reexpresa en inventory.txt los parches que el port hace a inventory.bin (alijo de 14 columnas y
ranuras extra del mercenario) y lo comprueba compilando el txt al formato del .bin.
uso: inventario_txt.py <excel_vanilla> <salida_excel>   (escribe inventory.txt y base/inventory.txt)"""
import sys, os, struct
PARTS = ['rArm', 'torso', 'lArm', 'head', 'neck', 'rHand', 'lHand', 'belt', 'feet', 'gloves']
COLS = 14

def lee(p):
    L = open(p, encoding='latin-1', newline='').read().split('\r\n')
    if L[-1] == '': L.pop()
    return [l.split('\t') for l in L]

def compila(rows):
    h = rows[0]; ix = {n.strip(): i for i, n in enumerate(h)}
    recs = [r for r in rows[1:] if r[0] != 'Expansion']
    out = bytearray(struct.pack('<I', len(recs)))
    v = lambda r, n: int(r[ix[n]]) if r[ix[n]].strip() != '' else 0
    for r in recs:
        b = struct.pack('<4i', v(r, 'invLeft'), v(r, 'invRight'), v(r, 'invTop'), v(r, 'invBottom'))
        b += struct.pack('<BBxx', v(r, 'gridX') & 255, v(r, 'gridY') & 255)
        b += struct.pack('<4i', v(r, 'gridLeft'), v(r, 'gridRight'), v(r, 'gridTop'), v(r, 'gridBottom'))
        b += struct.pack('<BBxx', v(r, 'gridBoxWidth') & 255, v(r, 'gridBoxHeight') & 255)
        for p in PARTS:
            b += struct.pack('<4i', v(r, p + 'Left'), v(r, p + 'Right'), v(r, p + 'Top'), v(r, p + 'Bottom'))
            b += struct.pack('<BBxx', v(r, p + 'Width') & 255, v(r, p + 'Height') & 255)
        assert len(b) == 240
        out += b
    return bytes(out)

def parche_port(inv):   # copia literal de la lógica de dm/ios/tools/wide_stash.py build()
    inv = bytearray(inv)
    for row in (10, 25):
        o = 4 + row * 240 + 16; assert inv[o:o + 2] == b'\x0a\x0a'; inv[o] = COLS
    for row, dx, dy in ((11, -320, 0), (26, -240, 60)):
        base = 4 + row * 240 + 0x28
        for k in range(4, 10):
            l, r, t, b_, x = struct.unpack_from('<5i', inv, 4 + 0x28 + k * 0x14)
            struct.pack_into('<5i', inv, base + k * 0x14, l + dx, r + dx, t + dy, b_ + dy, x)
    return bytes(inv)

def modifica(rows):
    h = rows[0]; ix = {n.strip(): i for i, n in enumerate(h)}; by = {r[0]: r for r in rows[1:]}
    for n in ('Big Bank Page 1', 'Big Bank Page2'): by[n][ix['gridX']] = str(COLS)
    src = by['Amazon']
    for n, dx, dy in (('Hireling', -320, 0), ('Hireling2', -240, 60)):
        for p in PARTS[4:]:
            for c, d in (('Left', dx), ('Right', dx), ('Top', dy), ('Bottom', dy)):
                by[n][ix[p + c]] = str(int(src[ix[p + c]]) + d)
            for c in ('Width', 'Height'): by[n][ix[p + c]] = src[ix[p + c]]
    return rows

van, out = sys.argv[1], sys.argv[2]; ok = True
for sub in ('', 'base/'):
    rows = lee(os.path.join(van, sub, 'inventory.txt')); vbin = open(os.path.join(van, sub, 'inventory.bin'), 'rb').read()
    c0 = compila(rows)
    d0 = [i for i in range(max(len(c0), len(vbin))) if i >= len(c0) or i >= len(vbin) or c0[i] != vbin[i]]
    print(f'{sub}inventory: compilar(txt vanilla) vs bin vanilla: {len(d0)} bytes distintos', d0[:8])
    m = modifica(rows); c1 = compila(m); want = parche_port(vbin)
    d1 = [i for i in range(len(want)) if c1[i] != want[i]] if len(c1) == len(want) else ['tamaño']
    print(f'{sub}inventory: compilar(txt modificado) vs bin parcheado por el port: {len(d1)} bytes distintos', d1[:8])
    ok &= not d1
    os.makedirs(os.path.join(out, sub), exist_ok=True)
    open(os.path.join(out, sub, 'inventory.txt'), 'w', encoding='latin-1', newline='').write('\r\n'.join('\t'.join(r) for r in m) + '\r\n')
sys.exit(0 if ok else 1)
