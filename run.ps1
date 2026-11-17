# Regenerate the submission: execute the notebook, validate the CSV with the official validator, print its SHA-256.
#
#     powershell -ExecutionPolicy Bypass -File run.ps1
#
# Expected SHA-256 of submissions/MesQueUnData.csv:
#     8ba09b17d35612bcd39e362819f75aef22c16a2416b426803e60fddf49cbacf2

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "No .venv. See README: py -3.11 -m venv .venv; pip install -r requirements-lock.txt" }
$nb = Join-Path $root "notebooks\pipeline\MesQueUnData.ipynb"

Write-Host "==> executing $nb"
& $py -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 `
    --ExecutePreprocessor.kernel_name=mesqueundata $nb
if ($LASTEXITCODE -ne 0) { throw "notebook failed" }

$csv = Join-Path $root "submissions\MesQueUnData.csv"
Push-Location (Join-Path $root "external\more-than-a-hack-2027")
& $py evaluation\validate_submission.py $csv
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { throw "official validation failed" }
(Get-FileHash $csv -Algorithm SHA256).Hash.ToLower()
