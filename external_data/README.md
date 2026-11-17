# External data

The datasets used by this pipeline that are **not** part of the competition bundle. All of them are public and cover
**other matches** (RULES.md: *"External data about other games"*). None of them is stored in this repository. They are
fetched from their owners at the exact version we used:

```powershell
powershell -ExecutionPolicy Bypass -File external_data\download_external_data.ps1            # all (± 5 GB)
powershell -ExecutionPolicy Bypass -File external_data\download_external_data.ps1 -Only idsse    # reproduction only (± 2.5 GB)
```
```bash
bash external_data/download_external_data.sh            # all
bash external_data/download_external_data.sh idsse      # reproduction only
```

Requirements: `git`, `git lfs` (for SkillCorner) and `curl`.

| Folder | Dataset | Source and pinned version | Labels (who, how many) | Used for | Needed to reproduce the CSV? |
|---|---|---|---|---|---|
| `idsse/` | IDSSE, 7 Bundesliga matches (Bassek et al. 2025), CC BY 4.0 | huggingface.co/datasets/pysport/idsse-data, revision `a715a38dfbaf5f58e431727c2b78d174101a703c`: 21 XML files (`DFL_02_01_*`, `DFL_03_02_*`, `DFL_04_03_*`) | provider's `BallStatus` and `BallPossession` flags | **validation only**: dead-ball boundaries and the ball-out rule (notebook section 8d) | **yes**, because `BALLOUT_STAGE = "auto"` re-runs the validation (or set `"force"`) |
| `skillcorner/` | SkillCorner Open Data, 20 A-League matches | github.com/SkillCorner/opendata, commit `4340d274572876239c154c90bc507a9b3250a656` (tracking files via Git LFS) | provider's event data (`player_possession`, `game_interruption_after`) | training the 6 possession models (section 6a) | no: the trained weights are in `notebooks/pipeline/models/` |
| `metrica/` | Metrica Sports Sample Games 1–3 | github.com/metrica-sports/sample-data, commit `e706dd506b360d69d9d123d5b8026e7294b13996` | provider's event data (PASS, SET PIECE, SHOT, RECOVERY, BALL LOST) | training the 6 possession models (section 6a) | no |

The 23 training matches are listed in `notebooks/pipeline/models/meta.json` (`training.matches`). The pinned
SkillCorner commit contains exactly these 20 matches. A newer commit may contain more, and the notebook trains on every
match folder it finds, so keep the pinned version when retraining.

## Retraining (optional)

The submitted CSV is regenerated from the shipped weights, so retraining is not needed. To retrain anyway, download
everything above and set in the first configuration cell of `notebooks/pipeline/MesQueUnData.ipynb`:

| Component | Setting | Data | Time (RTX 3050 Ti, 4 GB) |
|---|---|---|---|
| 6 possession models | `TRAIN_MODELS = True` | `skillcorner/`, `metrica/` | several GPU hours (5-fold CV + 6 final models) |
| YOLO26s ball detector | `YOLO_STAGE = "retrain"` | BAR-ATH tactical video (auto-labels, no hand labels) | ± 2 GPU hours |
| kit-colour classifiers (and all touch detection) | `TOUCH_STAGE = "retrain"` | BAR-ATH videos (auto-labels from tracking + homography) | recomputes person detection and touches on both videos |

GPU training is not bit-for-bit deterministic (`cudnn.deterministic` is off because it makes the TCN about 55× slower),
so retrained weights are close to the shipped ones but not identical, and the CSV can differ slightly. Exact
reproduction of the submitted file uses the shipped weights (`notebooks/pipeline/models/meta.json` holds their SHA-256).
