# Ball possession from automatic tracking — technical document

**Team:** Més Que Un Data — Raya Ramadha Fitroh, Fauzan Ahsanudin Alfikri, Gabriel Edbert Liandrew, Benedict Brian Joel Purba, Yan Ardhinaya Ardika · **Repository:** https://github.com/RayaRamadha/Mes-Que-Un-Data · **File:** _(final name set at submission)_ · **CSV SHA-256:** _(filled in at submission)_

> **Status: draft (21 Oct 2026), pipeline version v4.** Structure follows SUBMISSION.md. To be finalised before
> submission and exported to a PDF named after the team. Aggregate numbers only — no frame-level data appears in this
> document. Every public-ground-truth number refers to the first 5 minutes of play (17 possessions) and is used as a
> correctness check only. An Indonesian working copy is kept in `docs/technical_report_id.md`.

## 1. Summary

We split the task into two decisions and solve each as a **segmentation**, not a per-frame classification:
(1) **is the ball alive or dead**, using collective player and ball features, "anchors" of near-certain evidence,
the broadcast feed as a second witness, and a two-state Viterbi decoder; (2) **which team has the ball**, using a logistic model of **team shape** (width,
spread, relative speed) trained on *pseudo-labels* of "clear control" mined from the whole match — without any ground
truth — so that it also works on the ± 41% of graded frames where the ball is not tracked. A three-state Viterbi
decoder (H/A/D) combines both, with switching costs expressed in "seconds of evidence". On the public ground truth,
version v4 reaches **spellF1 ± 0.67 [0.44 – 0.83]** (official baseline ± 0.33 [0.21 – 0.45]) and macroF1 ± 0.89.
The broadcast recording, which is not synchronised, is aligned to the tactical timeline through player positions alone.
The whole pipeline is a sequence of Jupyter notebooks run by a single command and produces a byte-identical file.

## 2. Approach and rationale

**The metric shapes the design.** spellF1 counts each possession once. The two most expensive errors are a
*spurious switch* (`H H A H H` splits one possession into three) and a *spurious dead ball* inside a possession
(`H D H`). Every component therefore produces **segments** and is more reluctant to change state than a per-frame
classifier would be.

**Architecture.**

```
ATD + Smart Tagging ─► 01 preprocess ─► 03 dead ball (alive/dead + restarts) ─┐
broadcast ATD + homography ─┘ (alignment, ball, broadcast view)                  │
                                    └─► 04 features ─► 05 team-shape model ────┴─► 06 H/A/D decoder ─► CSV
```

| Stage | Core |
|---|---|
| `01` broadcast | broadcast ↔ tactical alignment by matching player positions (constant offset per half); broadcast ball fills tactical ball gaps; per-frame broadcast view (pitch / replay or close-up) |
| `03` dead ball | 7 collective features (players calm relative to the local norm, no passing activity, ball gap, ball near a line, **broadcast showing a replay or close-up**, slow ball, set-piece window) with principled weights; **anchors** of ±3 per frame: contested ball → alive, ball ≥ 1 m outside the pitch for ≥ 1 s → dead, ball gap ≥ 10 s → dead; two-state Viterbi (switch cost 20, minimum segment 2 s); bias chosen so the dead-ball share equals a prior of **0.48**; every dead segment must contain at least one stoppage cue |
| `04`–`05` team | pseudo-labels of "clear control" (a player ≤ 1.5 m from an observed ball, no opponent within 3 m, for ≥ 0.5 s) → logistic regression (IRLS + L2) on 6 smoothed (± 2 s) home-minus-away team-shape differences; out-of-fold predictions over time blocks; plus β × "team nearest to the ball", with β ≈ 1.0 estimated without ground truth |
| `06` decoder | per-half H/A/D Viterbi; `D` comes from stage 03; an H↔A switch costs 1 s × median \|log-odds\|; the first 2 s after a corner, goal kick or free kick are given to the taking team |

**Why not a model trained on the ground truth?** The public ground truth has 17 possessions and 4 dead-ball
segments — too few to train on, and EVALUATION.md shows that even a single hyperparameter chosen there can be wrong.
We used it only to understand the definitions (`02`) and to check correctness. Every parameter comes from football or
physical reasoning, or from the match itself (pseudo-labels, anchors, ground-truth-free proxies).

## 3. Assets used and dropped

| Asset | Used? | What for / why not |
|---|---|---|
| Tactical ATD | **yes** — main source | player positions and speeds per track slot, ball position; team per slot from the XML |
| Smart Tagging | **partly** | `SET PIECES` windows and start times (weak feature + stoppage cue), `Kick Off (After Goal)` (hard rule), `Team` of corners / goal kicks / free kicks = **taking team** (verified geometrically: for 12/12 corners the ball lies in the opponent half of the tagged team). Phase tags (Build Up, Defending…) are **not** used: in the public window they agree with possession on only 60–76% of frames — phases are not possessions |
| Tactical homography | no | the ATD is already in pitch coordinates; checked valid on 100% of frames |
| Broadcast ATD + homography | **yes** | aligned to tactical through player positions (offset constant per half: ± 160.6 s and ± 1076.8 s, negligible drift; players match within ± 0.75 m, ball within ± 0.8 m). Uses: (1) the broadcast ball fills tactical gaps (ball available on 59% → ± 63% of graded frames; 39% of live frames without a tactical ball recovered); (2) the broadcast view — when the director shows a replay or close-up (invalid homography, 33% of graded frames) players move like in a dead ball (± 1.0 vs ± 2.1 m/s), so it is dead-ball evidence |
| Tactical / broadcast video | no | — |
| Public ground truth (5 min) | checks only | understanding the definition of `D` and of switches (`02`); bootstrap-interval scores as correctness checks |
| External knowledge | yes | dead-ball share ≈ 0.48 from typical LaLiga effective playing time (± 50–56 of ± 95–100 minutes) |

## 4. Handling missing and noisy tracking

- **The ball is missing on 41% of graded frames, almost entirely in long gaps** (150 gaps, median ± 11 s; gaps
  ≤ 1 s account for 0.1% of missing frames). Linear interpolation is applied only to physically plausible gaps
  ≤ 1 s (41 frames); the aligned broadcast ball fills a further 8% of missing frames. Possession must therefore
  mostly be inferred from the players: the team-shape model reaches ± 0.92 team
  accuracy on the public ground truth, **including when the ball is not visible**.
- **Long ball gaps are evidence of a dead ball.** Shown without ground truth: inside gaps ≥ 10 s the median player
  speed is 0.8–1.1 m/s — slower than groups that are certainly dead (before kick-off 1.3; ball out of play 1.5) and
  far from contested balls (2.3). There are ± 79 such gaps.
- **Anonymous, duplicated and missing track slots.** All features are collective per team (range, variance, mean),
  never per player; shape features are `NaN` when fewer than 6 slots of a team are tracked (± 6% of frames).
  Per-slot speeds are clipped at 12 m/s to discard identity jumps.
- **Ball position jumps** (> 3 m per frame, 13 graded frames) are only flagged; ball features use median smoothing.
- **Attacking direction** is read from the XML and verified against player positions before both kick-offs.

## 5. Possession rules implemented

- **Dead ball (`D`)**: segments from detector `03`. Forced to `D`: the second half before kick-off (FAQ.md) and the
  window before each kick-off after a goal. Segments shorter than 2 s and segments without any stoppage cue (ball gap,
  ball out of play, ball placed still, start of a set-piece tag) are removed.
- **"Controlled" change of possession**: the new team must accumulate net evidence worth ± 1 s of ordinary evidence
  (the Viterbi cost). A momentary touch is not enough.
- **Loose balls, duels, deflections**: frames without the ball or with balanced evidence do not move the decision, so
  possession stays with the last team — as CHALLENGE.md specifies. Our analysis (`02`) supports this: in most public
  ground-truth switches the new team is already nearest to the ball 1–3 s *before* the label changes.
- **Restarts**: the first 2 s after a corner, goal kick or free kick belong to the taking team (from the tag).
  Throw-ins carry no team in the tags; their possession is decided by the decoder from ordinary evidence.
- **`X`**: not used on graded frames (the decoder always decides); only on ungraded frames.

## 6. Validation

**Protocol.** (1) The public ground truth is a correctness check only, with the official bootstrap intervals;
(2) ground-truth-free proxies over the whole match; (3) stability — parameters sit on plateaus, not on sharp peaks.
A change is adopted only if the proxies improve and the public score does not get worse. Every experiment is logged
in `docs/experiment_log.md`.

**Version history (public ground truth).**

| Version | Change | spellF1 [5–95%] | macroF1 | team accuracy (alive frames) |
|---|---|---|---|---|
| official baseline | nearest player + ± 50 majority vote | 0.33 [0.21 – 0.45] | 0.62 | 0.83 |
| v0 | dead-ball detector v3 + Viterbi on nearest team | 0.34 [0.19 – 0.50] | 0.72 | 0.69 |
| v1 | + team-shape model | 0.54 [0.32 – 0.74] | 0.77 | 0.75 |
| v2 | + anchors and passing activity in `D` | 0.59 [0.37 – 0.77] | 0.86 | 0.89 |
| v3 | + stoppage-cue requirement, restart prior | 0.64 [0.40 – 0.81] | 0.87 | 0.90 |
| **v4** | + broadcast: ball fills gaps, replay/close-up as dead-ball evidence | **0.67 [0.44 – 0.83]** | **0.89** | **0.90** |

**Dead-ball detector — ablation with ground-truth-free proxies** (same dead-ball share).

| Variant | contested frames labelled `D` | ball-out frames labelled `D` | gap ≥ 10 s labelled `D` | public precision / recall |
|---|---|---|---|---|
| features only | 20% | 85% | 79% | 0.52 / 0.91 |
| + anchors + passing activity | 0.7% | 96% | 100% | 0.80 / 0.81 |
| + stoppage-cue requirement | 1.3% | 97.5% | 100% | 0.85 / 0.81 |
| + broadcast ball and replay/close-up feature (final) | 1.0% | 96.9% | 100% | 0.86 / 0.86 |

**Team-shape model.** Blocked cross-validation on held-out pseudo-labels: AUC ± 0.91 (worst block ± 0.82). The
reliability of "nearest team" estimated without ground truth (q ± 0.73) matches what the public ground truth shows
(± 74%).

**Rejected experiments** (`07`): "clear control" anchors in the decoder (more possessions, not better), moving
boundaries to the first touch / first free control of the new team (our boundaries show no systematic bias; the public
score drops), and correcting the lag of the team-shape evidence (± 4 s, measured without ground truth, but correcting it
makes things worse).

**Sensitivity.** The public score is identical for switching costs of 0.25–1.5 s; dead-ball proxies are stable for
dead-ball share priors of 0.45–0.48 and degrade from 0.51; anchor strengths of 1–6 and dead-ball Viterbi costs of
10–40 do not change the picture.

## 7. Limitations and what we would improve with more time

- **Very short possessions** (≤ 1–2 s) leave almost no trace in automatic tracking and are not detected; 3 of the
  17 public possessions are of this kind.
- **Team-shape evidence lags by ± 4 s** after the ball changes hands; short possessions of 3–8 s are often merged.
- **Short dead balls with the ball not tracked** (e.g. quick throw-ins) can still be missed when the broadcast stays on
  the pitch; ball gaps of 3–10 s mix live and dead play.
- **The dead-ball share depends on a prior** from general knowledge (0.48).
- **The taking team of throw-ins** is not available from the tags.
- Next steps: ball detection from the tactical video to fill remaining gaps; a duration model (HSMM); sharper
  ball-based timing of switches.

## 8. Reproduction

```bash
git clone --recurse-submodules https://github.com/RayaRamadha/Mes-Que-Un-Data.git
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
powershell -ExecutionPolicy Bypass -File run_all.ps1      # -> submissions/MesQueUnData_<version>.csv
```

Place the data in `tactical/` and `broadcast/` at the repository root (or point `MTAH_DATA_DIR` at it). Notebook `00`
verifies the data and the environment (35 checks). Measured on a clean clone with a fresh virtual environment
(21 Oct 2026): installation ± 2.5 min, full pipeline (notebooks 00–07) ± 3.5 min on a laptop CPU. The SHA-256 of the
generated CSV must equal the one given at the top of this document; for the current version v4 it is
`627a5cc0d79798dc70db0d3087cfdb13c889dc8d08131eea306425c08de56afe`.
