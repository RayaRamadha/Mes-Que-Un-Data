# Download the external datasets at the exact versions used by the pipeline (see external_data/README.md).
#
#     powershell -ExecutionPolicy Bypass -File external_data\download_external_data.ps1               # all
#     powershell -ExecutionPolicy Bypass -File external_data\download_external_data.ps1 -Only idsse   # reproduction only
#
# Needs git, git lfs (SkillCorner tracking files) and curl.exe (shipped with Windows 10+). Folders that already exist
# are left untouched.
param([ValidateSet("all", "idsse", "training")] [string]$Only = "all")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$SC_COMMIT = "4340d274572876239c154c90bc507a9b3250a656"
$ME_COMMIT = "e706dd506b360d69d9d123d5b8026e7294b13996"
$ID_REV = "a715a38dfbaf5f58e431727c2b78d174101a703c"
$ID_MATCHES = @("DFL-COM-000001_DFL-MAT-J03WMX", "DFL-COM-000001_DFL-MAT-J03WN1", "DFL-COM-000002_DFL-MAT-J03WOH",
    "DFL-COM-000002_DFL-MAT-J03WOY", "DFL-COM-000002_DFL-MAT-J03WPY", "DFL-COM-000002_DFL-MAT-J03WQQ",
    "DFL-COM-000002_DFL-MAT-J03WR9")
$ID_KINDS = @("DFL_02_01_matchinformation", "DFL_03_02_events_raw", "DFL_04_03_positions_raw_observed")

function Invoke-Native { param([scriptblock]$cmd) & $cmd; if ($LASTEXITCODE -ne 0) { throw "failed: $cmd" } }

if ($Only -in "all", "idsse") {
    $dir = Join-Path $here "idsse"
    New-Item -ItemType Directory -Force $dir | Out-Null
    foreach ($m in $ID_MATCHES) {
        foreach ($k in $ID_KINDS) {
            $f = "{0}_{1}.xml" -f $k, $m
            $dst = Join-Path $dir $f
            if (Test-Path $dst) { Write-Host "exists  idsse/$f"; continue }
            Write-Host "get     idsse/$f"
            Invoke-Native { curl.exe -L -f -sS -o "$dst.part" "https://huggingface.co/datasets/pysport/idsse-data/resolve/$ID_REV/$f" }
            Move-Item "$dst.part" $dst
        }
    }
    Write-Host ("idsse: {0} of 21 XML files" -f (Get-ChildItem $dir -Filter *.xml).Count)
}

if ($Only -in "all", "training") {
    $sc = Join-Path $here "skillcorner"
    if (Test-Path $sc) { Write-Host "exists  skillcorner/ (left untouched)" } else {
        $env:GIT_LFS_SKIP_SMUDGE = "1"
        Invoke-Native { git clone --no-checkout https://github.com/SkillCorner/opendata.git $sc }
        Invoke-Native { git -C $sc -c advice.detachedHead=false checkout $SC_COMMIT }
        Remove-Item Env:GIT_LFS_SKIP_SMUDGE
        Invoke-Native { git -C $sc lfs pull --include "data/matches/**" }
    }
    $me = Join-Path $here "metrica"
    if (Test-Path $me) { Write-Host "exists  metrica/ (left untouched)" } else {
        Invoke-Native { git clone --no-checkout https://github.com/metrica-sports/sample-data.git $me }
        Invoke-Native { git -C $me -c advice.detachedHead=false checkout $ME_COMMIT }
    }
    Write-Host ("skillcorner: {0} matches (expected 20) | metrica: {1} sample games (expected 3)" -f `
        (Get-ChildItem (Join-Path $sc "data\matches") -Directory).Count, (Get-ChildItem (Join-Path $me "data") -Directory -Filter "Sample_Game_*").Count)
}
