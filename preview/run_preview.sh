#!/usr/bin/env bash
# Start the live application preview (viewing helper - NOT part of the delivered package).
#
# The sandbox resets between sessions, so this script installs the two viewing-only
# dependencies if they are missing and then serves preview/app_preview.ipynb, which builds
# the real AppShell from the workspace package and loads examples/GRR-01.json.
#
# Usage:  bash preview/run_preview.sh          (or:  npm-style one-liner in the chat)
set -euo pipefail
cd "$(dirname "$0")/.."

python - <<'PY'
import importlib.util as spec
import subprocess
import sys

missing = [name for name in ("ipywidgets", "voila") if not spec.find_spec(name)]
if missing:
    print("installing viewing-only dependencies:", ", ".join(missing))
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
print("viewing dependencies ready")
PY

exec voila --no-browser --port=8866 --Voila.ip=0.0.0.0 \
  --Voila.tornado_settings="{'headers': {'Content-Security-Policy': 'frame-ancestors *'}}" \
  preview/app_preview.ipynb
