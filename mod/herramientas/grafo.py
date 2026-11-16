#!/usr/bin/env python3
"""Inicios de función (destinos de bl) y llamadores. grafo.py <dir_hex>... -> función que contiene cada dir y quién la llama."""
import sys, struct, bisect, pickle, os
IMG = '/mnt/trabajo/dm-work/mod/main34.img'; CACHE = '/mnt/trabajo/dm-work/mod/grafo34.pkl'
def carga():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, 'rb'))
    img = open(IMG, 'rb').read(); n = 0x1b786a0 // 4; w = struct.unpack_from('<%dI' % n, img, 0)
    calls = {}
    for i, x in enumerate(w):
        if x >> 26 == 0x25:
            off = x & 0x3ffffff
            if off & (1 << 25): off -= 1 << 26
            calls.setdefault((i + off) * 4, []).append(i * 4)
    g = (sorted(calls), calls); pickle.dump(g, open(CACHE, 'wb')); return g
def func(starts, a): return starts[bisect.bisect_right(starts, a) - 1]
if __name__ == '__main__':
    starts, calls = carga()
    for a in sys.argv[1:]:
        a = int(a, 16); f = func(starts, a)
        print(f'{a:x} en func {f:x}; llamada desde', [f'{c:x}(func {func(starts, c):x})' for c in calls.get(f, [])][:8])
