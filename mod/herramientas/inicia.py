#!/usr/bin/env python3
"""Ejecuta los constructores globales (.init_array) del main en el emulador."""
import sys, struct, time
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import emu
def init_array(e):
    img = e.img; mod = struct.unpack_from('<I', img, 4)[0]; dyn = mod + struct.unpack_from('<i', img, mod + 4)[0]; d = {}
    o = dyn
    while True:
        tag, val = struct.unpack_from('<QQ', img, o); o += 16
        if tag == 0: break
        d[tag] = val
    a, n = d[25], d[27] // 8
    return [e.q(a + 8 * k) for k in range(n)]
def inicia(e, verbose=True):
    fs = init_array(e); fallos = []
    for k, f in enumerate(fs):
        if f in (0, 0xffffffffffffffff): continue
        try: e.call(f, maxins=50_000_000)
        except emu.Falta as x: fallos.append((k, f, str(x)))
    if verbose: print(f'constructores: {len(fs)}, fallidos: {len(fallos)}')
    return fallos
if __name__ == '__main__':
    e = emu.Emu(); t = time.time(); fl = inicia(e); print('%.1fs' % (time.time() - t))
    from collections import Counter
    c = Counter(m.split('(')[0][:90] for _, _, m in fl)
    for m, n in c.most_common(25): print(n, m)
    print('vtable 0x3115be8:', e.mem(0x3115be8, 16).hex(), '| 0x3115c30:', e.mem(0x3115c30, 8).hex())
