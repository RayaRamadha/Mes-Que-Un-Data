#!/usr/bin/env bash
# Regenerate the submission: execute the notebook, validate the CSV with the official validator, print its SHA-256.
#     bash run.sh
# Expected SHA-256 of submissions/MesQueUnData.csv:
#     8ba09b17d35612bcd39e362819f75aef22c16a2416b426803e60fddf49cbacf2
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
py="$root/.venv/bin/python"
[ -x "$py" ] || py="$root/.venv/Scripts/python.exe"
nb="$root/notebooks/pipeline/MesQueUnData.ipynb"
echo "==> executing $nb"
"$py" -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 \
    --ExecutePreprocessor.kernel_name=mesqueundata "$nb"
csv="$root/submissions/MesQueUnData.csv"
(cd "$root/external/more-than-a-hack-2027" && "$py" evaluation/validate_submission.py "$csv")
sha256sum "$csv" 2>/dev/null || shasum -a 256 "$csv"
