#!/bin/bash
# Sustituye el ejecutable del contenedor publicado por el compilado en CI y deja un zip que d2rm_pack.py acepta.
# uso: monta_contenedor.sh <contenedor publicado .zip> <DmIOS compilado en CI> <zip de salida>
set -euo pipefail
SRC=$(realpath "$1"); EXE=$(realpath "$2"); OUT=$(realpath -m "$3"); T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
( cd "$T" && unzip -q "$SRC" )
file "$EXE" | grep -q 'Mach-O 64-bit arm64 executable' || { echo "no es un ejecutable arm64 de iOS: $EXE"; exit 1; }
cp "$EXE" "$T/Payload/DmIOS.app/DmIOS"; chmod 755 "$T/Payload/DmIOS.app/DmIOS"
rm -f "$OUT"; python3 - "$T" "$OUT" <<'PY'
import os, sys, zipfile
raiz, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for d, _, fs in sorted(os.walk(raiz)):
        for f in sorted(fs):
            p = os.path.join(d, f); z.write(p, os.path.relpath(p, raiz))
PY
echo "contenedor: $OUT ($(stat -c %s "$OUT") bytes)"
