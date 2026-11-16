#!/usr/bin/env python3
"""Emulador mínimo del main de Switch (ARM64) para ejecutar funciones sueltas con unicorn.
Imagen cargada en base 0 (dirección = main+0x...). Las importaciones y el asignador global del juego
se sirven desde Python; lo que no esté implementado para la ejecución y dice qué faltaba."""
import struct, pickle, sys
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UcError
from unicorn.arm64_const import *
sys.path.insert(0, '/mnt/trabajo/dm-work/mod/tools'); import imports

IMG = '/mnt/trabajo/dm-work/mod/main34.img'; REL = '/mnt/trabajo/dm-work/mod/rel34.pkl'
IMG_TOP = 0x4000000
TRAP = 0x10000000; TRAP_SZ = 0x100000
HEAP = 0x20000000; HEAP_SZ = 0x40000000
STACK = 0x70000000; STACK_SZ = 0x1000000
STOP = TRAP + TRAP_SZ - 8
GA_OBJ = 0x3211700 + 0x100   # no se usa: el objeto falso vive en el montón

class Falta(Exception): pass

import math
class Emu:
    CTYPE = {'isalpha': str.isalpha, 'isalnum': str.isalnum, 'isdigit': str.isdigit, 'isspace': str.isspace, 'isupper': str.isupper, 'islower': str.islower, 'isprint': str.isprintable, 'ispunct': lambda c: c.isprintable() and not c.isalnum() and c != ' ', 'isxdigit': lambda c: c in '0123456789abcdefABCDEF'}
    MATH = {'cosf': math.cos, 'sinf': math.sin, 'sqrtf': math.sqrt, 'tanf': math.tan, 'atanf': math.atan, 'expf': math.exp, 'logf': math.log, 'acosf': math.acos, 'asinf': math.asin, 'floorf': math.floor, 'ceilf': math.ceil}
    NOPS = ('_ZN2nn2os', '_ZN2nn2oe', '_ZN2nn4time', '_ZN2nn7friends', '_ZN2nn3hid', '_ZN2nn7account', 'nnos', 'sched_yield', 'pthread_mutex')
    def __init__(self, log=False):
        self.log = log
        self.img, self.got = imports.carga(IMG)
        u = self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        u.mem_map(0, IMG_TOP); u.mem_write(0, self.img)
        for a, v in pickle.load(open(REL, 'rb')).items(): u.mem_write(a, struct.pack('<Q', v))
        u.mem_map(TRAP, TRAP_SZ); u.mem_write(TRAP, struct.pack('<I', 0xd65f03c0) * (TRAP_SZ // 4))   # ret
        u.mem_map(HEAP, HEAP_SZ); self.brk = HEAP + 0x1000; self.sizes = {}
        u.mem_map(STACK, STACK_SZ)
        self.traps = {}; self.names = {}; self.calls = {}
        for slot, name in self.got.items():
            u.mem_write(slot, struct.pack('<Q', self.trap(name)))
        # asignador global del juego: [0x32116f8] -> objeto con vtable; byte de guarda en 0x3211700
        vt = self.alloc(0x200); obj = self.alloc(0x40)
        for k in range(0x40): u.mem_write(vt + 8 * k, struct.pack('<Q', self.trap('ga_vt_%x' % (8 * k))))
        u.mem_write(obj, struct.pack('<Q', vt)); u.mem_write(0x32116f8, struct.pack('<Q', obj)); u.mem_write(0x3211700, b'\x01')
        u.mem_write(0x3211710, struct.pack('<Q', vt)); u.mem_write(0x3211708, struct.pack('<Q', 0x3211710))   # asignador interno (su clase real vive en el SDK)
        u.reg_write(UC_ARM64_REG_CPACR_EL1, 3 << 20)   # habilita FP/SIMD
        u.hook_add(UC_HOOK_CODE, self._code, begin=TRAP, end=TRAP + TRAP_SZ)
        u.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        self.impl = {
            'memcpy': self.h_memcpy, 'memmove': self.h_memcpy, 'memset': self.h_memset, 'strlen': self.h_strlen,
            'strcmp': self.h_strcmp, 'strcasecmp': self.h_strcasecmp, 'strncmp': self.h_strncmp, 'memcmp': self.h_memcmp,
            'strncasecmp': self.h_strncasecmp, 'malloc': self.h_malloc, 'free': self.h_nop, 'calloc': self.h_calloc,
            'realloc': self.h_realloc, '_Znwm': self.h_malloc, '_Znam': self.h_malloc, '_ZdlPv': self.h_nop, '_ZdaPv': self.h_nop,
            'ga_vt_10': self.h_ga_alloc, 'ga_vt_28': self.h_nop, 'ga_vt_18': self.h_ga_realloc, 'ga_vt_20': self.h_ga_inplace,
            '__cxa_guard_acquire': self.h_guard, '__cxa_guard_release': self.h_guard_rel, 'strtol': self.h_strtol, 'strtoul': self.h_strtol, 'strtoll': self.h_strtol, 'strtoull': self.h_strtol, 'atoi': self.h_atoi,
            'strchr': self.h_strchr, 'toupper': self.h_toupper, 'tolower': self.h_tolower, 'strcpy': self.h_strcpy,
            '_ZN2nn3mem17StandardAllocator8AllocateEmm': self.h_sa_alloc, '_ZN2nn3mem17StandardAllocator8AllocateEm': self.h_sa_alloc,
            '_ZN2nn3mem17StandardAllocator4FreeEPv': self.h_nop, '_ZN2nn3mem17StandardAllocator10ReallocateEPvm': self.h_sa_realloc,
            'atof': self.h_atof, 'strtod': self.h_atof, 'strtof': self.h_atoff,
            'strcspn': self.h_strcspn, 'strspn': self.h_strspn, 'strpbrk': self.h_strpbrk, 'memchr': self.h_memchr, 'strcat': self.h_strcat, 'strnlen': self.h_strnlen, 'abs': lambda: self.ret(abs(self._s32(self.r(0)))),
            'qsort': self.h_qsort, 'vsnprintf': self.h_vsnprintf, 'vsprintf': self.h_vsprintf, 'snprintf': self.h_snprintf, 'sprintf': self.h_sprintf,
            'strncpy': self.h_strncpy, 'strstr': self.h_strstr, 'strrchr': self.h_strrchr,
        }
    # --- infraestructura
    def trap(self, name):
        if name not in self.traps:
            a = TRAP + 16 + 4 * len(self.traps); self.traps[name] = a; self.names[a] = name
        return self.traps[name]
    def alloc(self, n, align=16):
        n = max(int(n), 1); a = (self.brk + align - 1) & ~(align - 1); self.brk = a + n + 16
        if self.brk > HEAP + HEAP_SZ: raise Falta('montón agotado')
        self.sizes[a] = n; return a
    def r(self, k): return self.u.reg_read(UC_ARM64_REG_X0 + k)
    def ret(self, v=0): self.u.reg_write(UC_ARM64_REG_X0, v & 0xffffffffffffffff)
    def mem(self, a, n): return bytes(self.u.mem_read(a, n))
    def cstr(self, a, lim=4096):
        out = bytearray()
        while len(out) < lim:
            b = self.mem(a + len(out), 64); i = b.find(b'\0')
            if i >= 0: out += b[:i]; break
            out += b
        return bytes(out)
    def w(self, a, b): self.u.mem_write(a, bytes(b))
    def q(self, a): return struct.unpack('<Q', self.mem(a, 8))[0]
    def gancho(self, addr, fn):
        """Sustituye una función interna: su primera instrucción pasa a ser ret y fn() se ejecuta antes."""
        self.u.mem_write(addr, struct.pack('<I', 0xd65f03c0)); self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, _: fn(), begin=addr, end=addr)
    def espia(self, addr, fn):
        self.u.hook_add(UC_HOOK_CODE, lambda u, a, s, _: fn(), begin=addr, end=addr)
    def _code(self, u, addr, size, _):
        if addr == STOP: u.emu_stop(); return
        name = self.names.get(addr)
        if name is None: return
        self.calls[name] = self.calls.get(name, 0) + 1
        f = self.impl.get(name)
        if f is None and name in self.CTYPE: f = lambda: self.ret(1 if self.CTYPE[name](chr(self.r(0) & 255)) and (self.r(0) & 255) < 128 else 0)
        if f is None and name in self.MATH: f = lambda: self._f1(self.MATH[name])
        if f is None and name.startswith(self.NOPS): f = self.h_nop
        if f is None:
            self.err = Falta('importación sin implementar: %s (lr=%#x)' % (name, u.reg_read(UC_ARM64_REG_LR))); u.emu_stop(); return
        f()
    def _unmapped(self, u, access, addr, size, value, _):
        self.err = Falta('acceso a memoria sin mapear %#x (pc=%#x, lr=%#x)' % (addr, u.reg_read(UC_ARM64_REG_PC), u.reg_read(UC_ARM64_REG_LR))); return False
    def call(self, fn, *args, maxins=2_000_000_000):
        u = self.u; self.err = None
        for k, a in enumerate(args): u.reg_write(UC_ARM64_REG_X0 + k, a & 0xffffffffffffffff)
        u.reg_write(UC_ARM64_REG_SP, STACK + STACK_SZ - 0x10000); u.reg_write(UC_ARM64_REG_LR, STOP)
        try: u.emu_start(fn, STOP, count=maxins)
        except UcError as e:
            if not self.err: self.err = Falta('unicorn: %s (pc=%#x)' % (e, u.reg_read(UC_ARM64_REG_PC)))
        if self.err: raise self.err
        if u.reg_read(UC_ARM64_REG_PC) != STOP: raise Falta('no terminó: pc=%#x' % u.reg_read(UC_ARM64_REG_PC))
        return self.r(0)
    # --- libc
    def h_nop(self): self.ret(0)
    def h_guard(self):   # guarda de estáticos: 1 = hay que inicializar
        self.ret(0 if self.mem(self.r(0), 1)[0] & 1 else 1)
    def h_guard_rel(self): self.w(self.r(0), b'\x01'); self.ret(0)
    def h_memcpy(self):
        d, s, n = self.r(0), self.r(1), self.r(2)
        if n: self.w(d, self.mem(s, n))
        self.ret(d)
    def h_memset(self):
        d, c, n = self.r(0), self.r(1) & 255, self.r(2)
        if n: self.w(d, bytes([c]) * n)
        self.ret(d)
    def h_strlen(self): self.ret(len(self.cstr(self.r(0))))
    def _cmp(self, a, b): return (a > b) - (a < b)
    def h_strcmp(self): self.ret(self._cmp(self.cstr(self.r(0)), self.cstr(self.r(1))))
    def h_strcasecmp(self): self.ret(self._cmp(self.cstr(self.r(0)).lower(), self.cstr(self.r(1)).lower()))
    def h_strncmp(self): n = self.r(2); self.ret(self._cmp(self.cstr(self.r(0))[:n], self.cstr(self.r(1))[:n]))
    def h_strncasecmp(self): n = self.r(2); self.ret(self._cmp(self.cstr(self.r(0))[:n].lower(), self.cstr(self.r(1))[:n].lower()))
    def h_memcmp(self): n = self.r(2); self.ret(self._cmp(self.mem(self.r(0), n), self.mem(self.r(1), n)))
    def h_malloc(self): self.ret(self.alloc(self.r(0)))
    def h_calloc(self):
        n = self.r(0) * self.r(1); a = self.alloc(n); self.w(a, b'\0' * n); self.ret(a)
    def h_realloc(self):
        p, n = self.r(0), self.r(1); a = self.alloc(n)
        if p: self.w(a, self.mem(p, min(n, self.sizes.get(p, 0))))
        self.ret(a)
    def h_ga_alloc(self):
        n = self.r(1); a = self.alloc(n, max(self.r(2) & 0xffff, 16)); self.w(a, b'\0' * n); self.ret(a)
    def h_sa_alloc(self):
        n = self.r(1); a = self.alloc(n, max(self.r(2) & 0xffff, 16)); self.w(a, b'\0' * n); self.ret(a)
    def h_sa_realloc(self):
        p, n = self.r(1), self.r(2); a = self.alloc(n); self.w(a, b'\0' * n)
        if p: self.w(a, self.mem(p, min(n, self.sizes.get(p, 0))))
        self.ret(a)
    def h_ga_realloc(self):   # (self, ptr, tamaño, alineación)
        p, n = self.r(1), self.r(2)
        if not n: self.ret(0); return
        a = self.alloc(n, max(self.r(3) & 0xffff, 16)); self.w(a, b'\0' * n)
        if p: self.w(a, self.mem(p, min(n, self.sizes.get(p, 0))))
        self.ret(a)
    def h_ga_inplace(self):   # (self, ptr, tamaño): crecer en el sitio; solo si cabe en lo ya reservado
        p, n = self.r(1), self.r(2); self.ret(p if p and n <= self.sizes.get(p, 0) else 0)
    def h_strtol(self):
        s = self.cstr(self.r(0)).decode('latin-1'); base = self.r(2)
        import re
        m = re.match(r'\s*[-+]?(0[xX][0-9a-fA-F]+|\d+)', s)
        v = int(m.group(0), base or 0) if m else 0
        if self.r(1): self.w(self.r(1), struct.pack('<Q', self.r(0) + (m.end() if m else 0)))
        self.ret(v)
    def h_atoi(self):
        import re
        m = re.match(r'\s*[-+]?\d+', self.cstr(self.r(0)).decode('latin-1')); self.ret(int(m.group(0)) if m else 0)
    def h_strchr(self):
        s = self.cstr(self.r(0)); c = self.r(1) & 255; i = len(s) if c == 0 else s.find(bytes([c])); self.ret(self.r(0) + i if i >= 0 else 0)
    def h_strrchr(self):
        s = self.cstr(self.r(0)); i = s.rfind(bytes([self.r(1) & 255])); self.ret(self.r(0) + i if i >= 0 else 0)
    def h_strstr(self):
        i = self.cstr(self.r(0)).find(self.cstr(self.r(1))); self.ret(self.r(0) + i if i >= 0 else 0)
    def h_toupper(self): c = self.r(0); self.ret(c - 32 if 97 <= c <= 122 else c)
    def h_tolower(self): c = self.r(0); self.ret(c + 32 if 65 <= c <= 90 else c)
    def h_strcpy(self): s = self.cstr(self.r(1)); self.w(self.r(0), s + b'\0'); self.ret(self.r(0))
    def h_strncpy(self):
        n = self.r(2); s = self.cstr(self.r(1))[:n]; self.w(self.r(0), s + b'\0' * (n - len(s))); self.ret(self.r(0))
    def _num(self):
        import re
        m = re.match(r'\s*[-+]?(\d+\.?\d*([eE][-+]?\d+)?|\.\d+)', self.cstr(self.r(0)).decode('latin-1')); return float(m.group(0)) if m else 0.0
    def h_atof(self): self.u.reg_write(UC_ARM64_REG_D0, struct.unpack('<Q', struct.pack('<d', self._num()))[0])
    def h_atoff(self): self.u.reg_write(UC_ARM64_REG_S0, struct.unpack('<I', struct.pack('<f', self._num()))[0])
    def _f1(self, fn):
        x = struct.unpack('<f', struct.pack('<I', self.u.reg_read(UC_ARM64_REG_S0) & 0xffffffff))[0]
        try: y = fn(x)
        except (ValueError, OverflowError): y = 0.0
        self.u.reg_write(UC_ARM64_REG_S0, struct.unpack('<I', struct.pack('<f', y))[0])
    def sub(self, fn, *args):
        """Llama a código emulado desde dentro de un gancho (llamada anidada) y devuelve x0."""
        u = self.u; ctx = u.context_save(); sp = u.reg_read(UC_ARM64_REG_SP)
        for k, a in enumerate(args): u.reg_write(UC_ARM64_REG_X0 + k, a & 0xffffffffffffffff)
        u.reg_write(UC_ARM64_REG_SP, (sp - 0x2000) & ~15); u.reg_write(UC_ARM64_REG_LR, STOP)
        u.emu_start(fn, STOP); r = u.reg_read(UC_ARM64_REG_X0); u.context_restore(ctx); return r
    def h_qsort(self):
        base, n, sz, cmp_ = self.r(0), self.r(1), self.r(2), self.r(3)
        if n > 1:
            import functools
            items = [self.mem(base + i * sz, sz) for i in range(n)]
            a = self.alloc(sz); b = self.alloc(sz)
            def c(x, y):
                self.w(a, x); self.w(b, y); r = self.sub(cmp_, a, b) & 0xffffffff
                return r - (1 << 32) if r & 0x80000000 else r
            items.sort(key=functools.cmp_to_key(c)); self.w(base, b''.join(items))
        self.ret(0)
    def _fmt(self, fmt, nxt):
        import re
        out = b''; i = 0
        for m in re.finditer(rb'%([-+ 0#]*)(\d+|\*)?(?:\.(\d+|\*))?(hh|h|ll|l|z|j|t)?([diuxXcspf%eEgG])', fmt):
            out += fmt[i:m.start()]; i = m.end(); fl, wd, pr, ln, cv = m.groups(); cv = cv.decode()
            if cv == '%': out += b'%'; continue
            if wd == b'*': wd = str(nxt() & 0xffffffff).encode()
            if pr == b'*': pr = str(nxt() & 0xffffffff).encode()
            spec = '%' + fl.decode() + (wd or b'').decode() + ('.' + pr.decode() if pr is not None else '')
            if cv in 'fFeEgG': out += (spec + cv) .encode() % 0.0; continue   # flotantes: no se usan en la carga de tablas
            v = nxt()
            if cv == 's': t = self.cstr(v) if v else b'(null)'; out += (spec + 's').encode() % t
            elif cv == 'c': out += bytes([v & 255])
            elif cv == 'p': out += b'0x%x' % v
            else:
                bits = 64 if ln in (b'l', b'll', b'z', b'j', b't') else 32; v &= (1 << bits) - 1
                if cv in 'di' and v >> (bits - 1): v -= 1 << bits
                out += (spec + ('d' if cv in 'diu' else cv)).encode() % v
        return out + fmt[i:]
    def _va(self, ap):
        st = {'gr': struct.unpack('<i', self.mem(ap + 24, 4))[0], 'stk': self.q(ap), 'top': self.q(ap + 8)}
        def nxt():
            if st['gr'] < 0: v = self.q(st['top'] + st['gr']); st['gr'] += 8
            else: v = self.q(st['stk']); st['stk'] += 8
            return v
        return nxt
    def _regs(self, first):
        st = {'k': first, 'sp': self.u.reg_read(UC_ARM64_REG_SP)}
        def nxt():
            if st['k'] < 8: v = self.r(st['k']); st['k'] += 1
            else: v = self.q(st['sp']); st['sp'] += 8
            return v
        return nxt
    def _sal(self, dst, n, out):
        if n: self.w(dst, out[:n - 1] + b'\0')
        self.ret(len(out))
    def h_vsnprintf(self): self._sal(self.r(0), self.r(1), self._fmt(self.cstr(self.r(2)), self._va(self.r(3))))
    def h_vsprintf(self): self._sal(self.r(0), 1 << 20, self._fmt(self.cstr(self.r(1)), self._va(self.r(2))))
    def h_snprintf(self): self._sal(self.r(0), self.r(1), self._fmt(self.cstr(self.r(2)), self._regs(3)))
    def h_sprintf(self): self._sal(self.r(0), 1 << 20, self._fmt(self.cstr(self.r(1)), self._regs(2)))
    def _s32(self, v): v &= 0xffffffff; return v - (1 << 32) if v >> 31 else v
    def h_strcspn(self):
        s, rej = self.cstr(self.r(0)), self.cstr(self.r(1)); n = 0
        while n < len(s) and s[n] not in rej: n += 1
        self.ret(n)
    def h_strspn(self):
        s, acc = self.cstr(self.r(0)), self.cstr(self.r(1)); n = 0
        while n < len(s) and s[n] in acc: n += 1
        self.ret(n)
    def h_strpbrk(self):
        s, acc = self.cstr(self.r(0)), self.cstr(self.r(1))
        for i, c in enumerate(s):
            if c in acc: self.ret(self.r(0) + i); return
        self.ret(0)
    def h_memchr(self):
        i = self.mem(self.r(0), self.r(2)).find(bytes([self.r(1) & 255])); self.ret(self.r(0) + i if i >= 0 else 0)
    def h_strcat(self):
        d = self.r(0); self.w(d + len(self.cstr(d)), self.cstr(self.r(1)) + b'\0'); self.ret(d)
    def h_strnlen(self): self.ret(min(len(self.cstr(self.r(0))), self.r(1)))
    # --- utilidades del juego
    def vector(self, data):
        """Vector del juego {ptr, tamaño, capacidad}: el búfer con el fichero leído."""
        p = self.alloc(len(data) + 16); self.w(p, data + b'\0'); v = self.alloc(0x20)
        self.w(v, struct.pack('<QQQ', p, len(data), len(data))); return v
