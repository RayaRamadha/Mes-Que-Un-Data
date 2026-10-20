# Menjalankan seluruh pipeline: setiap notebook notebooks/NN_*.ipynb dieksekusi berurutan
# memakai .venv proyek. Berhenti pada notebook pertama yang gagal.
#
# Pemakaian (dari akar repo, PowerShell):
#     powershell -ExecutionPolicy Bypass -File run_all.ps1
#     powershell -ExecutionPolicy Bypass -File run_all.ps1 -From 03     # mulai dari notebook 03

param([string]$From = "00")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "venv belum ada. Jalankan: py -3.11 -m venv .venv; .venv\Scripts\python -m pip install -r requirements-lock.txt"
}

$notebooks = Get-ChildItem (Join-Path $root "notebooks") -Filter "*.ipynb" |
    Where-Object { $_.Name -match '^\d\d_' -and $_.Name.Substring(0, 2) -ge $From } |
    Sort-Object Name

foreach ($nb in $notebooks) {
    Write-Host "==> $($nb.Name)"
    & $py -m nbconvert --to notebook --execute --inplace `
        --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=python3 $nb.FullName
    if ($LASTEXITCODE -ne 0) { throw "gagal: $($nb.Name)" }
}
Write-Host "Selesai: $($notebooks.Count) notebook."
