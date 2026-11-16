#!/usr/bin/env python3
"""Compila una tabla .txt con el código del propio juego (emulado) y la compara con el .bin vanilla.
uso: compila_tabla.py <txt> <bin_de_referencia> <desc_hex> <desc_bytes_hex> <tam_registro> [modo]"""
import sys, struct
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import emu
txt, ref, desc, dsz, rec = sys.argv[1], sys.argv[2], int(sys.argv[3], 16), int(sys.argv[4], 16), int(sys.argv[5], 0)
modo = int(sys.argv[6]) if len(sys.argv) > 6 else 1
e = emu.Emu()
v = e.vector(open(txt, 'rb').read())
t = e.call(0xde2e80, v)
if not t: sys.exit('el analizador devolvió nulo')
n = struct.unpack('<I', e.mem(t + 0x20, 4))[0]; print('filas según el analizador:', n)
d = e.alloc(dsz); e.w(d, e.mem(desc, dsz))
out = e.alloc(n * rec + 64); e.w(out, b'\0' * (n * rec))
e.call(0xde3450, t, d, out, n, rec, modo)
got = struct.pack('<I', n) + e.mem(out, n * rec); want = open(ref, 'rb').read()
dif = [i for i in range(min(len(got), len(want))) if got[i] != want[i]]
print('tamaños', len(got), len(want), '| bytes distintos', len(dif), dif[:10], '| llamadas', e.calls)
sys.exit(0 if not dif and len(got) == len(want) else 1)
