# Final pipeline

`MesQueUnData.ipynb` is the whole pipeline in one notebook: the base pipeline plus **section 8d, "last touch
before the ball goes out"**. Sections 6d, 6e and 6f (smoothed-ball training, nearest-player method, stacking) and 8c
(switch re-timing) are kept as a record but switched off by default, because they were rejected by their decision
rules.

A few Indonesian names are kept in the code on purpose. They are keys stored with the models in `meta.json`, column
names, restart types read by `aturan_keluar.py`, or file names, and renaming them could change the output. The
glossary at the top of the notebook gives their English meaning.

## The rule

The Laws of the Game award a corner kick or goal kick to the **opponents** of the team that touched the ball last. So,
when the ball goes out, the possession belongs to the team that is not taking the restart (¬R). On BAR-ATH the base
prediction gives the ball to the restart taker right up to the moment it goes out in 17 of 21 corners.

## Two variants, validated on 7 IDSSE matches

IDSSE uses the DFL `BallPossession` flag (it changes at every touch) and the `BallStatus` flag. The log-odds come from
the final possession models, which never saw IDSSE.

| Variant | What it does | Δ spellF1 |
|---|---|---|
| terminal prior | forces ¬R in the last 0.2 s before the ball goes out; Viterbi decides when the switch happens | −0.0045 (0/7) |
| **proximity insertion** | if the label before the ball goes out is R: ¬R from the last ¬R touch (nearest ¬R player ≤ 1.5 m from the ball and closer than any R player, ≤ 5 s back) until the ball goes out | **+0.0065 [+0.004; +0.009] (7/7)** |

**Decision rule (fixed before the run):** the best variant is used if its mean Δ > 0 and the 5% bootstrap lower bound
(over matches) > 0. Only restarts whose taker is known from Smart Tagging (corner kicks, goal kicks) are used. Throw-ins
can be included with `BALLOUT_THROWIN = True`, but this is not validated for BAR-ATH because the tags carry no taker team.

On BAR-ATH this gives **13 inserted possessions** (median 2.1 s, 0.44% of graded frames). None of them fall in the
public 5-minute window, so the public score is unchanged (0.7412).

## Files

| File | Content |
|---|---|
| `models/` | the 6 possession models (BiGRU/TCN) trained on external open data, plus `meta.json` with their SHA-256 |
| `artefak/` + `pasang_artefak.py` | trained YOLO26s ball detector and kit-colour classifiers; the script installs them into `cache/` |
| `idsse_loader.py` | DFL XML parser → `cache/external/id_*.npz` (the first parse takes ± 2 minutes) |
| `aturan_keluar.py` | IDSSE restart detection, last-touch search, insertion variant, decoder |

## Running

Close other notebook kernels, then run `run.ps1` (or *Run All* with the kernel `Python 3.11 (.venv Més Que Un
Data)`). Nothing is trained. With the caches in place, section 8d takes ± 1 minute and the whole notebook ± 15–20
minutes. The repository README covers installation, data placement and the expected SHA-256.
