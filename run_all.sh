#!/usr/bin/env bash
# Menjalankan seluruh pipeline: setiap notebook notebooks/NN_*.ipynb dieksekusi berurutan
# memakai .venv proyek. Berhenti pada notebook pertama yang gagal.
#
#   ./run_all.sh          # semua
#   ./run_all.sh 03       # mulai dari notebook 03
set -euo pipefail

FROM="${1:-00}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then PY="$ROOT/.venv/Scripts/python.exe"   # Windows (Git Bash)
elif [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"                 # macOS / Linux
else echo "venv belum ada: python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements-lock.txt" >&2; exit 1
fi

n=0
for nb in "$ROOT"/notebooks/[0-9][0-9]_*.ipynb; do
  name="$(basename "$nb")"
  [[ "${name:0:2}" < "$FROM" ]] && continue
  echo "==> $name"
  "$PY" -m nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=python3 "$nb"
  n=$((n + 1))
done
echo "Selesai: $n notebook."
