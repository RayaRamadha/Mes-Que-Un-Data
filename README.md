# More than a Hack 2027: Ball Possession · team **Més Que Un Data**

Solution for [More than a Hack 2027, Phase 1](https://github.com/metrica-sports/more-than-a-hack-2027): one label
`H` / `A` / `D` / `X` for each of the 199,319 frames of the FC Barcelona – Athletic Club tactical video.

- **Submitted file:** [submissions/MesQueUnData.csv](submissions/MesQueUnData.csv), final pipeline, included in the
  repository. A run of the notebook overwrites it, so `git status` stays clean when the reproduction is byte-identical
- **SHA-256:** `8ba09b17d35612bcd39e362819f75aef22c16a2416b426803e60fddf49cbacf2`
- **Technical document:** [docs/technical_report.md](docs/technical_report.md)
- **Experiment log:** [docs/experiment_log.md](docs/experiment_log.md), 110 entries: what was tried, the evidence, and
  whether it was adopted or rejected

> **No match data is in this repository** (competition licence). `.gitignore` excludes `data/`, videos, `cache/` and
> `submissions/` (except the submitted file, which holds one H/A/D/X label per frame and nothing else). Notebook outputs are stripped on commit (`nbstripout`), because they contain match frames.

## What is here

```
notebooks/pipeline/
  MesQueUnData.ipynb            the whole pipeline in one notebook (markdown explains every step; glossary of kept names)
  models/                       6 possession models (BiGRU/TCN) trained on external open data + meta.json (SHA-256)
  artefak/                      trained YOLO26s ball detector + kit-colour classifiers (installed by pasang_artefak.py)
  idsse_loader.py               IDSSE (DFL) XML parser, used to validate the ball-out rule
  aturan_keluar.py              Laws-of-the-Game rule "last touch before the ball goes out" (section 8d)
  pasang_artefak.py             copies artefak/ into cache/
external/more-than-a-hack-2027/ official repository (git submodule): games.py, scorer, public 5-minute GT
run.ps1 / run.sh                one command: run the notebook, validate the CSV, print its SHA-256
requirements.txt / -lock.txt    pinned dependencies (Python 3.11, PyTorch 2.6 CUDA 12.4)
```

## 1. Install (Python 3.11)

```bash
git clone --recurse-submodules https://github.com/RayaRamadha/Mes-Que-Un-Data.git
cd Mes-Que-Un-Data
py -3.11 -m venv .venv                                         # macOS/Linux: python3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt   # macOS/Linux: .venv/bin/python
.venv\Scripts\python -m ipykernel install --sys-prefix --name mesqueundata --display-name "Python 3.11 (.venv Més Que Un Data)"
.venv\Scripts\python -m ipykernel install --sys-prefix --name python3
```

Installing takes ± 2–3 minutes plus the PyTorch CUDA wheel (2.5 GB).

## 2. Data

| What | Where | Needed for |
|---|---|---|
| competition bundle: `BAR-ATH_tactical_*` (ATD xml/txt, homography, smart tagging, **video**) | `data/tactical/` | everything |
| `BAR-ATH_broadcast_*` (ATD xml/txt, homography, **video**) | `data/broadcast/` | everything |
| IDSSE, 7 matches (`DFL_02_01_*`, `DFL_03_02_*`, `DFL_04_03_*` XML) from huggingface.co/datasets/pysport/idsse-data (CC BY 4.0) | `external_data/idsse/` | section 8d validation (or set `BALLOUT_STAGE = "force"`) |
| SkillCorner Open Data, Metrica sample data | `external_data/skillcorner`, `external_data/metrica` | only for **retraining** the possession models (not needed: weights are included) |

`MTAH_DATA_DIR` may point to another folder that contains `tactical/` and `broadcast/`.

The external datasets are not stored here. [external_data/README.md](external_data/README.md) lists their sources,
pinned versions and labels, and one script downloads them at the exact versions we used:
`powershell -ExecutionPolicy Bypass -File external_data\download_external_data.ps1 -Only idsse` (reproduction) or
without `-Only` (everything, for retraining; `bash external_data/download_external_data.sh` on macOS/Linux). The same
file explains how to retrain the models.

## 3. Run

```bash
.venv\Scripts\python notebooks\pipeline\pasang_artefak.py        # once: installs the trained YOLO / kit weights
powershell -ExecutionPolicy Bypass -File run.ps1                 # or: bash run.sh
```

The script executes the notebook, writes `submissions/MesQueUnData.csv`, runs the official
`validate_submission.py`, and prints the SHA-256. That hash must equal the one above. You can also open the notebook
with the kernel *Python 3.11 (.venv Més Que Un Data)* and choose *Run All*.

**Runtime** on a laptop with an RTX 3050 Ti (4 GB) and 16 GB RAM:

| Run | Time | Notes |
|---|---|---|
| first run | ± 2.5–3 h | ball detection over the whole tactical video (YOLO, about 1.5–2 h), touch detection on both videos, audio whistle scores; IDSSE parsing takes 2 min |
| later runs | ± 15–20 min | everything is cached in `cache/`; nothing is trained, because the possession models, YOLO and kit weights are included |

Close other heavy applications first: the notebook peaks at about 4.5 GB RAM.

## 4. Pipeline in one paragraph

The ball signal comes from three sources: tactical tracking, the broadcast ball (aligned through player positions)
and our own YOLO26 detector trained on auto-labelled tactical frames. Dead ball is detected from collective
behaviour, snapped to restart kicks and line crossings, and backed by a whistle rule from the audio. An ensemble of
six sequence models trained on 23 external labelled matches gives H/A log-odds. A three-state Viterbi decoder combines
them with touch evidence from both videos (kit colour + contact). Finally, a Laws-of-the-Game rule restores the last
touch before corners and goal kicks; it was validated on 7 IDSSE matches.

Every choice was made by leave-match-out cross-validation on external data. The public 5-minute GT is used only as a
correctness check. Details are in [docs/technical_report.md](docs/technical_report.md).
