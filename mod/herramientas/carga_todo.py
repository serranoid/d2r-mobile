#!/usr/bin/env python3
"""Ejecuta (emulada) la carga completa de tablas del juego en modo txt y compara cada tabla compilada
con su .bin de referencia.  uso: carga_todo.py <dir_excel_txt> <dir_excel_bin_ref> [dir_salida]
Con MOD=<carpeta con data/...> en el entorno, sus ficheros tienen prioridad sobre los vanilla (como el overlay)."""
import sys, os, struct
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import emu
TXT, REF = sys.argv[1], sys.argv[2]; OUT = sys.argv[3] if len(sys.argv) > 3 else None
e = emu.Emu()
import inicia; inicia.inicia(e)
e.w(0x21278b9, b'\x01')            # modo txt
RAIZ = os.path.abspath(os.path.join(TXT, '..', '..', '..'))   # la carpeta que contiene data/
estado = {'ult': None}; leidos = []; comp = []; abiertos = {}
MOD = os.environ.get('MOD')
def resuelve(path):
    for raiz in ([MOD] if MOD else []) + [RAIZ]:
        f = resuelve1(path, raiz)
        if f: return f
def resuelve1(path, raiz):
    rel = path.replace('\\', '/').lower(); i = rel.find('data/')
    rel = rel[i:] if i >= 0 else rel.lstrip('/'); cur = raiz
    for part in rel.split('/'):
        m = [f for f in os.listdir(cur) if f.lower() == part] if os.path.isdir(cur) else []
        if not m: return None
        cur = os.path.join(cur, m[0])
    return cur if os.path.isfile(cur) else None
# objeto fichero del motor: vt+0x38 tamaño, vt+0x10 leer(buf, &n), vt+0x58 dueño (cuyo vt+0x18 cierra)
VT = e.alloc(0x100); DUEÑO = e.alloc(0x20); VTD = e.alloc(0x100)
for k in range(0x20): e.w(VT + 8 * k, struct.pack('<Q', e.trap('f_vt_%x' % (8 * k)))); e.w(VTD + 8 * k, struct.pack('<Q', e.trap('fd_vt_%x' % (8 * k))))
e.w(DUEÑO, struct.pack('<Q', VTD))
def abre():
    path = e.cstr(e.r(0)).decode('latin-1'); f = resuelve(path); rel = path.replace('\\', '/').lower(); estado['ult'] = rel[rel.find('excel/') + 6:] if 'excel/' in rel else rel.split('/')[-1]
    if f is None: leidos.append((path, None)); e.ret(0); return
    data = open(f, 'rb').read(); o = e.alloc(0x200); e.w(o, b'\0' * 0x200); e.w(o, struct.pack('<Q', VT)); abiertos[o] = data
    leidos.append((path, len(data))); e.ret(o)
def f_tam(): e.ret(len(abiertos[e.r(0)]))
def f_lee():
    d = abiertos[e.r(0)]; n = min(e.q(e.r(2)), len(d)); e.w(e.r(1), d[:n]); e.w(e.r(2), struct.pack('<Q', n)); e.ret(1)
e.impl.update({'f_vt_38': f_tam, 'f_vt_10': f_lee, 'f_vt_58': lambda: e.ret(DUEÑO), 'fd_vt_18': e.h_nop})
e.gancho(0xde5cf0, abre)
def existe():   # (vista {ptr, largo}, banderas) -> ¿existe el fichero?
    v = e.r(0); path = e.mem(e.q(v), e.q(v + 8)).decode('latin-1'); ok = resuelve(path) is not None
    leidos.append((path + ' [¿existe?]', 1 if ok else None)); e.ret(1 if ok else 0)
e.gancho(0x1af8040, existe)
def reserva2():   # asignador del segundo montón del motor: (tamaño, alineación)
    n = e.r(0); a = e.alloc(n, max(e.r(1) & 0xffff, 16)); e.ret(a)
e.gancho(0xdf9c00, reserva2)
def tlsf():   # memalign del montón por bloques del motor: (montón, alineación, tamaño)
    n = e.r(2); a = e.alloc(n, max(e.r(1) & 0xffff, 16)); e.ret(a)
e.gancho(0x1b63900, tlsf)
pend = []
def compila(): pend.append((estado['ult'], e.r(2), e.r(3) & 0xffffffff, e.r(4) & 0xffffffff))
def libera():   # el .bin se escribiría justo aquí: foto del resultado antes de que nada lo retoque
    while pend:
        name, out, n, rec = pend.pop(0); comp.append((name, n, rec, e.mem(out, n * rec)))
e.espia(0xde3450, compila); e.espia(0xde3350, libera)
# tabla de cadenas del juego: mapa {nº de cubos, cubos} en main+0x2d70ff0; nodo {sig, clave, largo, id u16}.
# El id es el campo "id" de los JSON de idioma. Se rellena con la función de hash del propio juego.
def cadenas(dirjson, mapa=0x2d70ff0, NB=1 << 15):
    import json, glob
    cub = e.alloc(NB * 8); e.w(cub, b'\0' * (NB * 8)); tmp = e.alloc(16); n = 0; heads = {}
    for f in sorted(glob.glob(os.path.join(dirjson, '*.json'))):
        for it in json.load(open(f, encoding='utf-8-sig')):
            k = it['Key'].encode('latin-1', 'replace'); kp = e.alloc(len(k) + 1); e.w(kp, k + b'\0')
            e.call(0x1b6e1e0, tmp, kp, len(k), 0); h = e.q(tmp) & (NB - 1)
            nodo = e.alloc(0x20); e.w(nodo, struct.pack('<QQQHxxxxxx', heads.get(h, 0), kp, len(k), it['id'] & 0xffff)); heads[h] = nodo; n += 1
    for h, nodo in heads.items(): e.w(cub + 8 * h, struct.pack('<Q', nodo))
    e.w(mapa, struct.pack('<QQ', NB, cub)); e.w(0x2d71098, b'\x01'); return n
STR = os.path.join(RAIZ, 'data', 'local', 'lng', 'strings')
print('cadenas cargadas:', cadenas(STR))
avisos = []
def aviso():
    t = []
    for k in range(5):
        v = e.r(k)
        try: c = e.cstr(v, 120) if 0x1000 < v < 0x80000000 else None
        except Exception: c = None
        t.append(c.decode('latin-1') if c and all(9 <= x < 127 for x in c) and len(c) > 1 else hex(v))
    avisos.append((estado['ult'], t, hex(e.u.reg_read(emu.UC_ARM64_REG_LR)))); e.ret(0)
e.gancho(0xde1850, aviso)
malos = {}
VACIA = e.alloc(0x80); e.w(VACIA, b'\0' * 0x80)
nulos = {}
def enlace():
    if e.r(0) == 0:
        nulos[estado['ult']] = nulos.get(estado['ult'], 0) + 1; e.u.reg_write(emu.UC_ARM64_REG_X0, VACIA); return   # búsqueda en una tabla de enlaces: si su mapa no está inicializado (estado del motor que aquí no existe), se vacía
    o = e.r(0); b = e.q(o + 0x20)
    if b and (e.q(o + 0x18) == 0 or not (emu.HEAP <= b < emu.HEAP + emu.HEAP_SZ or b < emu.IMG_TOP)):
        k = (hex(o), estado['ult'], e.cstr(e.r(1))[:24]); malos[k] = malos.get(k, 0) + 1; e.w(o + 0x18, struct.pack('<QQ', 0, 0))
e.espia(0xde4880, enlace)
err = None
try:
    e.call(0x4da800)          # mismo orden que el arranque real (main+0x240d64...): contextos, sonidos, tablas
    try: e.call(0x34ebd0, 0)
    except emu.Falta as x: print('carga de sonidos: sigue hacia el motor de audio y se corta ahí (esperado):', str(x)[:60])
    e.call(0x4db130, 0)
except emu.Falta as x: err = x
print('ficheros pedidos:', len(leidos), '| tablas compiladas:', len(comp))
ok = mal = sin = 0
libera()
for name, n, rec, datos in comp:
    b = (name or '?').rsplit('.', 1)[0]; ref = None; sub, base = os.path.split(b); d0 = os.path.join(REF, sub)
    for f in (os.listdir(d0) if os.path.isdir(d0) else []):
        if f.lower() == base + '.bin': ref = open(os.path.join(d0, f), 'rb').read()
    got = struct.pack('<I', n) + datos
    if OUT: os.makedirs(os.path.join(OUT, sub), exist_ok=True); open(os.path.join(OUT, b + '.bin'), 'wb').write(got)
    if ref is None or len(ref) != len(got): sin += 1; continue
    d = sum(1 for i in range(min(len(got), len(ref))) if got[i] != ref[i])
    if d == 0 and len(got) == len(ref): ok += 1
    else:
        offs = sorted({(i - 4) % rec for i in range(4, len(got)) if got[i] != ref[i]})
        mal += 1; print(f'  {b}: {n}x{rec}; bytes distintos {d} en {len(offs)} posiciones del registro: {offs[:40]}')
print(f'idénticas {ok}, distintas {mal}, sin .bin comparable (pasadas de índice) {sin}')
print('no encontrados:', [p for p, n in leidos if n is None][:20])
print('avisos del compilador:', len(avisos))
for a in avisos[:12]: print('   ', a)
print('búsquedas en tabla de enlace nula, por fichero:', nulos)
print('tablas de enlace sin inicializar:', list(malos.items())[:12], len(malos))
if err: print('PARÓ:', err); print('último fichero:', estado['ult'])
if err:
    sp = e.u.reg_read(emu.UC_ARM64_REG_SP)
    print('retornos en pila:', [hex(v) for v in struct.unpack('<400Q', e.mem(sp, 3200)) if 0x1000 < v < 0x1b786a0 and v % 4 == 0][:16])
