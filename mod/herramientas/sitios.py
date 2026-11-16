#!/usr/bin/env python3
"""Lista las llamadas al cargador de tablas (main+0x4d9040): nombre, descriptor de campos, tamaño de registro."""
import sys, struct, re
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import desens
img = desens.img
def sitios():
    t = 0x4d9040; out = []
    for a in range(0, 0x1b786a0, 4):
        w = struct.unpack_from('<I', img, a)[0]
        if w >> 26 != 0x25: continue
        off = w & 0x3ffffff
        if off & (1 << 25): off -= 1 << 26
        if a + off * 4 != t: continue
        L = desens.run(a - 4 * 60, 60)
        name = desc = dsz = rec = None; pend = None
        for l in L:
            m = re.search(r'add x1, x1, #0x[0-9a-f]+  ; -> (0x[0-9a-f]+) "([^"]+)"', l)
            if m: name = m.group(2)
            m = re.search(r'add x1, x1, #0x[0-9a-f]+  ; -> (0x[0-9a-f]+)$', l)
            if m: pend = int(m.group(1), 16)
            m = re.search(r'mov w2, #(0x[0-9a-f]+|\d+)$', l)
            if m: psz = int(m.group(1), 0)
            if 'memcpy' in l and pend: desc, dsz, pend = pend, psz, None
            m = re.search(r'mov w5, #(0x[0-9a-f]+|\d+)$', l)
            if m: rec = int(m.group(1), 0)
        out.append((a, name, desc, dsz, rec))
    return out
if __name__ == '__main__':
    for a, name, desc, dsz, rec in sitios():
        print(f'{a:x}\t{name}\t{desc and hex(desc)}\t{dsz and hex(dsz)}\t{rec}')
