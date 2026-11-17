#!/usr/bin/env bash
# Download the external datasets at the exact versions used by the pipeline (see external_data/README.md).
#
#     bash external_data/download_external_data.sh            # all
#     bash external_data/download_external_data.sh idsse      # reproduction only
#     bash external_data/download_external_data.sh training   # SkillCorner + Metrica (retraining only)
#
# Needs git, git lfs (SkillCorner tracking files) and curl. Folders that already exist are left untouched.
set -euo pipefail
ONLY="${1:-all}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SC_COMMIT=4340d274572876239c154c90bc507a9b3250a656
ME_COMMIT=e706dd506b360d69d9d123d5b8026e7294b13996
ID_REV=a715a38dfbaf5f58e431727c2b78d174101a703c
ID_MATCHES="DFL-COM-000001_DFL-MAT-J03WMX DFL-COM-000001_DFL-MAT-J03WN1 DFL-COM-000002_DFL-MAT-J03WOH
DFL-COM-000002_DFL-MAT-J03WOY DFL-COM-000002_DFL-MAT-J03WPY DFL-COM-000002_DFL-MAT-J03WQQ DFL-COM-000002_DFL-MAT-J03WR9"
ID_KINDS="DFL_02_01_matchinformation DFL_03_02_events_raw DFL_04_03_positions_raw_observed"

if [ "$ONLY" = all ] || [ "$ONLY" = idsse ]; then
  mkdir -p "$HERE/idsse"
  for m in $ID_MATCHES; do
    for k in $ID_KINDS; do
      f="${k}_${m}.xml"
      if [ -f "$HERE/idsse/$f" ]; then echo "exists  idsse/$f"; continue; fi
      echo "get     idsse/$f"
      curl -L -f -sS -o "$HERE/idsse/$f.part" "https://huggingface.co/datasets/pysport/idsse-data/resolve/$ID_REV/$f"
      mv "$HERE/idsse/$f.part" "$HERE/idsse/$f"
    done
  done
  echo "idsse: $(ls "$HERE/idsse"/*.xml | wc -l) of 21 XML files"
fi

if [ "$ONLY" = all ] || [ "$ONLY" = training ]; then
  if [ -e "$HERE/skillcorner" ]; then echo "exists  skillcorner/ (left untouched)"; else
    GIT_LFS_SKIP_SMUDGE=1 git clone --no-checkout https://github.com/SkillCorner/opendata.git "$HERE/skillcorner"
    GIT_LFS_SKIP_SMUDGE=1 git -C "$HERE/skillcorner" -c advice.detachedHead=false checkout "$SC_COMMIT"
    git -C "$HERE/skillcorner" lfs pull --include "data/matches/**"
  fi
  if [ -e "$HERE/metrica" ]; then echo "exists  metrica/ (left untouched)"; else
    git clone --no-checkout https://github.com/metrica-sports/sample-data.git "$HERE/metrica"
    git -C "$HERE/metrica" -c advice.detachedHead=false checkout "$ME_COMMIT"
  fi
  echo "skillcorner: $(ls -d "$HERE/skillcorner/data/matches"/*/ | wc -l) matches (expected 20) | metrica: $(ls -d "$HERE/metrica/data"/Sample_Game_*/ | wc -l) sample games (expected 3)"
fi
