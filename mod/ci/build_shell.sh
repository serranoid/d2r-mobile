#!/bin/bash
# Compila en macOS solo el contenedor de iOS (sin contenido del juego) a partir de este árbol.
# Entra: el código del repo y mod/ci/stubs/ (tablas vacías con su tamaño y la tabla numérica de niveles).
# Sale: out/DmIOS.app con el ejecutable del host; el .ipa se monta después en local con d2rm_pack.py.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); IOS=$ROOT/dm/ios; ST=$ROOT/mod/ci/stubs
CHAIN=$(cat "$ROOT/mod/ci/CHAIN")
# Xcode más nuevo con SDK de iOS
best=; for x in /Applications/Xcode*.app; do v=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$x/Contents/version.plist" 2>/dev/null || echo 0); echo "xcode: $x $v"; if [ -z "$best" ] || [ "$(printf '%s\n%s\n' "$v" "$bv" | sort -V | tail -1)" = "$v" ]; then best=$x; bv=$v; fi; done
export DEVELOPER_DIR=$best/Contents/Developer; echo "usando $best ($bv), SDK $(xcrun --sdk iphoneos --show-sdk-version)"
cp "$ST/dm_vault_tab.h" "$ST/dm_hud_exp.h" "$ST/dm_bright_levels.inc" "$ROOT/dm/host/"
cp "$ST/dm_touch_native_art.c" "$IOS/Sources/"
printf '// CI: cadena de shaders que espera el contenedor publicado\n#define DMSH_CHAIN "%s"\n' "$CHAIN" > "$ROOT/dm/gfx/nvn/dmsh_chain.h"
cd "$IOS"; rm -rf Gen; mkdir -p Gen/dm
python3 tools/gen_build.py ../host Gen > Gen/dm.xcconfig
echo '// contenedor: los módulos del juego se cargan de Guest.framework (DM_SHELL)' > Gen/embed.S
sed -i '' -e 's/^OTHER_CFLAGS = \$(inherited) /OTHER_CFLAGS = $(inherited) -DDM_SHELL /' Gen/dm.xcconfig
printf 'OTHER_LDFLAGS = $(inherited) $(DM_FRAMEWORKS)\n' >> Gen/dm.xcconfig
grep -q -- '-DDM_SHELL' Gen/dm.xcconfig
for d in assets/NativeHUD/v4/hud_v4_ui assets/NativeHUD/mapgoal romfs_overlay romfs_overlay_variants romfs_overlay_astc romfs_overlay_astc_variants msl save_ref save_ref_warlock; do mkdir -p "Gen/$d"; echo ci > "Gen/$d/.ci_placeholder"; done
echo '{}' > Gen/assets/NativeHUD/v4/hud.json   # el paso previo de Xcode solo comprueba que existe
cp ../gfx/nvn/shader_map.tsv ../gfx/nvn/pso_manifest.tsv asset_pointers.txt Gen/dm/
export DM_BUNDLE_ID=org.d2rmobile.app DM_TEAM_ID=0000000000 DM_FREE_ACCOUNT=1
python3 tools/project_free.py project.yml project_free.yml
xcodegen generate --spec project_free.yml
set -o pipefail
xcodebuild -project DmIOS.xcodeproj -scheme DmIOS -configuration Release -destination 'generic/platform=iOS' -derivedDataPath "$ROOT/build_ci" \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY= DM_DEVICE_FAMILY=1,2 COMPILER_INDEX_STORE_ENABLE=NO build 2>&1 | tee "$ROOT/build_ci.log" | grep -E 'error:|warning: unused|BUILD|^\*\*|Ld |CompileC .*(main|front_ios)' | cut -c1-300 || true
APP=$(ls -d "$ROOT"/build_ci/Build/Products/Release-*/DmIOS.app | head -1)
mkdir -p "$ROOT/out"; cp -R "$APP" "$ROOT/out/DmIOS.app"
find "$ROOT/out/DmIOS.app" -name .ci_placeholder -delete
( cd "$ROOT/out" && find DmIOS.app -type f | sort | while read -r f; do printf '%s\t%s\n' "$(stat -f %z "$f")" "$f"; done ) | tee "$ROOT/out/files.tsv" | tail -40
shasum -a 256 "$ROOT/out/DmIOS.app/DmIOS"; file "$ROOT/out/DmIOS.app/DmIOS"
