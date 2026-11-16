#!/usr/bin/env python3
"""dis.py <dir_hex> [n_insns|hasta ret]  -> desensamblado anotado (imports, cadenas adrp+add)."""
import sys, struct, capstone
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import imports
img, got = imports.carga()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
def cstr(a):
    if not (0x1b79000 <= a < 0x2060000): return None
    e = img.find(b'\0', a); s = img[a:e]
    if 2 <= len(s) < 80 and all(32 <= c < 127 for c in s): return s.decode()
def run(a, lim=None):
    page = {}; out = []
    n = 0
    while True:
        w = img[a:a+4]; i = next(md.disasm(w, a), None)
        if i is None: out.append(f'{a:x}: ??'); a += 4; n += 1; continue
        note = ''
        if i.mnemonic == 'adrp':
            r, v = i.op_str.split(', #'); page[r] = int(v, 16)
        elif i.mnemonic == 'add' and i.op_str.count(',') == 2:
            d, s, v = [x.strip() for x in i.op_str.split(',')]
            if s in page and v.startswith('#'):
                t = page[s] + int(v[1:], 16); c = cstr(t); note = f'  ; -> {t:#x}' + (f' "{c}"' if c else '')
        elif i.mnemonic in ('ldr', 'ldrb', 'strb', 'str', 'ldrh', 'ldrsw') and '[' in i.op_str and '#' in i.op_str:
            import re
            m = re.search(r'\[(x\d+), #(0x[0-9a-f]+|\d+)\]', i.op_str)
            if m and m.group(1) in page: note = f'  ; [{page[m.group(1)] + int(m.group(2), 0):#x}]'
        elif i.mnemonic in ('bl', 'b') and i.op_str.startswith('#'):
            t = int(i.op_str[1:], 16); nm = imports.plt_name(img, got, t)
            if nm: note = '  ; ' + nm
        out.append(f'{a:x}: {i.mnemonic} {i.op_str}{note}')
        a += 4; n += 1
        if lim and n >= lim: break
        if not lim and i.mnemonic == 'ret': break
    return out
if __name__ == '__main__':
    print('\n'.join(run(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else None)))
