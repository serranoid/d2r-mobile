#!/usr/bin/env python3
"""xref.py <img> <dir_hex>... : lista los sitios de código (adrp+add / adrp+ldr) que resuelven a cada dirección."""
import sys, struct
img = open(sys.argv[1], 'rb').read(); TEXT_END = int(sys.argv[2], 16); targets = {int(a, 16) for a in sys.argv[3:]}
pages = {t & ~0xfff for t in targets}; hits = {t: [] for t in targets}
w = struct.unpack_from('<%dI' % (TEXT_END // 4), img, 0)
for i, ins in enumerate(w):
    if ins & 0x9f000000 != 0x90000000: continue   # adrp
    rd = ins & 31; imm = ((ins >> 5) & 0x7ffff) << 2 | ((ins >> 29) & 3)
    if imm & (1 << 20): imm -= 1 << 21
    page = ((i * 4) & ~0xfff) + (imm << 12)
    if page not in pages: continue
    for j in range(i + 1, min(i + 8, len(w))):
        n = w[j]
        if n & 0xffc00000 == 0x91000000 and ((n >> 5) & 31) == rd:   # add xd, xn, #imm12
            a = page + ((n >> 10) & 0xfff)
            if a in targets: hits[a].append(j * 4)
            break
for t in sorted(hits): print(hex(t), [hex(x) for x in hits[t]][:12], len(hits[t]))
