#!/usr/bin/env python3
"""rango.py <ini> <fin> [todo] -> desensamblado de un rango; sin 'todo', solo llamadas, comparaciones, saltos y constantes."""
import sys, re
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import desens
a, b = int(sys.argv[1], 16), int(sys.argv[2], 16); todo = len(sys.argv) > 3
for l in desens.run(a, (b - a) // 4):
    m = l.split(': ', 1)[1]
    if todo or re.match(r'(bl|blr|b\.|cb|tb|cmp|cmn|tst|ret|br|b )', m) or '; ->' in l or re.search(r'mov w\d+, #0x[0-9a-f]{2,}', m): print(l[:120])
