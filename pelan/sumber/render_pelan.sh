#!/usr/bin/env bash
# Render pelan.html -> JPG resolusi tinggi + PDF A3 (raster ~290 dpi) resolusi tinggi dengan Chromium tanpa kepala.
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
SCALE="${SCALE:-3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 jana_pelan.py
"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --virtual-time-budget=4000 \
  --force-device-scale-factor="$SCALE" --window-size=1588,1400 \
  --screenshot="$TMP/pelan.png" "file://$PWD/pelan.html" 2>/dev/null
SCALE="$SCALE" TMP="$TMP" python3 - <<'PY'
import os
from PIL import Image
s = float(os.environ['SCALE'])
im = Image.open(os.environ['TMP'] + '/pelan.png').convert('RGB')
im = im.crop((0, 0, round(420 / 25.4 * 96 * s), round(297 / 25.4 * 96 * s)))
im.save('../Pelan_Lantai_Bawah_A3.jpg', quality=92, optimize=True)
im.save('../Pelan_Lantai_Bawah_A3.pdf', resolution=96 * s, quality=92)
im.resize((im.width // 3, im.height // 3), Image.LANCZOS).save('../Pelan_Lantai_Bawah_pratonton.jpg', quality=88)
print(im.size)
PY
