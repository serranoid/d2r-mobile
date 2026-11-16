#!/usr/bin/env python3
"""Mapa GOT -> nombre de símbolo importado, y stub PLT -> nombre, del main (imagen base 0)."""
import struct, pickle, sys
def carga(path='/mnt/trabajo/dm-work/mod/main34.img'):
    img = open(path, 'rb').read()
    mod = struct.unpack_from('<I', img, 4)[0]
    assert img[mod:mod+4] == b'MOD0', img[mod:mod+4]
    dyn = mod + struct.unpack_from('<i', img, mod + 4)[0]
    d = {}
    o = dyn
    while True:
        tag, val = struct.unpack_from('<QQ', img, o); o += 16
        if tag == 0: break
        d[tag] = val
    symtab, strtab = d[6], d[5]
    def name(i):
        st_name = struct.unpack_from('<I', img, symtab + 24 * i)[0]
        e = img.index(b'\0', strtab + st_name); return img[strtab + st_name:e].decode()
    got = {}
    for tab, sz in ((d.get(23), d.get(2)), (d.get(7), d.get(8))):
        if not tab: continue
        for k in range(sz // 24):
            off, info, add = struct.unpack_from('<QQq', img, tab + 24 * k)
            sym = info >> 32
            if sym: got[off] = name(sym)
    return img, got
def plt_name(img, got, a):
    w = struct.unpack_from('<4I', img, a)
    if (w[0] & 0x9f00001f) != 0x90000010: return None
    immlo = (w[0] >> 29) & 3; immhi = (w[0] >> 5) & 0x7ffff
    page = ((a >> 12) + ((immhi << 2) | immlo)) << 12
    off = ((w[1] >> 10) & 0xfff) * 8
    return got.get(page + off)
if __name__ == '__main__':
    img, got = carga()
    print(len(got), 'imports')
    for a in sys.argv[1:]:
        a = int(a, 16); print(hex(a), plt_name(img, got, a))
