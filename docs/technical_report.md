# Ball possession from automatic tracking: technical document

**Team:** Més Que Un Data (Raya Ramadha Fitroh, Fauzan Ahsanudin Alfikri, Gabriel Edbert Liandrew, Benedict Brian Joel
Purba, Yan Ardhinaya Ardika)
**Repository:** https://github.com/RayaRamadha/Mes-Que-Un-Data
**Submitted file:** `MesQueUnData.csv`
**CSV SHA-256:** `8ba09b17d35612bcd39e362819f75aef22c16a2416b426803e60fddf49cbacf2`

> Only aggregate numbers appear in this document. Every number on the public ground truth (GT) refers to the published
> 5-minute window (17 possessions). We used that window as a correctness check only, never to choose a method or a
> parameter. One possession there is worth about 6 spellF1 points.

## 1. Executive summary

**Goal.** Label every frame of FC Barcelona vs Athletic Club with the team in possession (`H`, `A`) or a dead ball
(`D`), using only automatic tracking, tagging and video, and score as high as possible on the ranking metric spellF1.

**Approach.** We treat the task as time-series segmentation scored per possession. A possession model learns from 23
other matches with open possession labels. Its output is combined with dead-ball detection and touch evidence from the
two videos, then decoded into segments with an explicit cost for every change of possession.

**Main components.**

1. **Ball.** A fused ball signal from the tactical tracking, the broadcast tracking (aligned through player positions)
   and our own YOLO26 ball detector trained on automatic labels from the tactical video.
2. **Dead ball `D`.** A detector based on collective player behaviour, with boundaries snapped to physical events
   (restart kick, ball crossing a line) and a referee-whistle rule read from the video audio.
3. **Team in possession.** An ensemble of six sequence models (BiGRU and TCN with a player-set encoder) trained on 20
   SkillCorner and 3 Metrica matches, plus touch evidence from the tactical and broadcast videos (who touched the ball,
   identified by kit colour), decoded by a three-state Viterbi decoder.
4. **Laws-of-the-Game rule.** Before a corner or goal kick, the opponents of the taker touched the ball last. When
   our labels contradict this, the opponents' last touch is inserted as a possession.

**Result.** Public GT (correctness check only): **spellF1 0.741 [0.577–0.882]**, macroF1 0.906, alive/dead F1 0.970,
17 predicted possessions vs 17 true. The official baseline scores 0.33 [0.21–0.45]. Leave-match-out cross-validation
on the 23 external matches, scored over full matches with the official spellF1: **≈ 0.81** under this match's ball-gap
pattern, ≈ 0.84 with the ball visible.

## 2. Task definition

**Input.** One match, 199,319 frames at 25 fps. Provided assets: tactical and broadcast automatic tracking (ATD) with
homographies, Smart Tagging, the tactical video and the broadcast video.

**Output.** One label per frame:

| Label | Meaning |
|---|---|
| `H` | home team (FC Barcelona) in possession, ball alive |
| `A` | away team (Athletic Club) in possession, ball alive |
| `D` | dead ball: the ball is not in play |
| `X` | no answer; frames without GT are never scored |

A change of possession happens when a player of the other team gains controlled possession. While play is live there
is always one team in possession, so a loose ball stays with the last team. Dead-ball ownership is not asked for.

**Evaluation objective.** The ranking metric is **spellF1**. A possession is a maximal run of `H` or `A`. Predicted
possessions are matched one-to-one with true ones by temporal IoU, and the F1 of that matching is averaged over IoU
thresholds 0.3–0.7. Every possession counts once, whatever its length. **macroF1** (mean per-class F1 of `H`, `A`, `D`
per frame) is the first tie-break.

## 3. Problem formulation and methodology

**The metric decides the architecture.** spellF1 punishes two errors that per-frame accuracy hides:

- *spurious switches*: `H H A H H` turns one possession into three;
- *missed short possessions*: a 1-second interception between two long possessions merges them.

Every stage therefore produces segments, not independent frames. The final labels come from a decoder with an explicit
switching cost, so a change of team has to be paid for with evidence.

**Learning from other matches.** The public GT holds 17 possessions, far too few to train or select on. The rules allow
external data, so we built a benchmark from **20 SkillCorner Open Data matches + 3 Metrica Sports sample matches**
(about 6,000 labelled possessions). All design choices were made with leave-match-out cross-validation on these
matches: architecture, features, augmentation, decoder cost and every rule. On these matches the score of the first
5 minutes is almost uncorrelated with the full-match score, which confirms that the public window cannot rank methods.

**Signals the tracking cannot give.** Automatic tracking loses the ball for long stretches (available on 59% of graded
frames here) and does not show who touched it. We add two signals from the videos: our own ball detector, and touch
evidence (ball contact plus the kit colour of the toucher). The dead-ball state is a separate problem with its own
detector, because its cues (player behaviour, lines, whistles, set-piece tags) differ from those of possession.

**Laws of the Game as constraints.** Some situations have a known answer from the Laws: a corner or goal kick is
awarded against the team that touched the ball last. We encode such constraints as rules on top of the decoder, and
only after they pass validation on an external dataset with possession flags (IDSSE).

## 4. System architecture

The pipeline is one notebook, `notebooks/pipeline/MesQueUnData.ipynb`. The data flow is:

1. tactical and broadcast tracking → aligned and fused ball, with gaps filled by the YOLO video ball;
2. tracking, ball, Smart Tagging, broadcast view and audio → dead-ball segments `D`;
3. tracking and ball → 47 features per step at 10 fps → six sequence models → H/A log-odds;
4. videos → touches, toucher team by kit colour → touch evidence;
5. log-odds, touch evidence and `D` → three-state Viterbi decoder → labels;
6. Laws-of-the-Game rule → final labels → CSV at 25 fps.

| Stage | Method | Evidence (no BAR-ATH GT used) |
|---|---|---|
| Broadcast alignment | one time offset per half, found by matching player positions (mode of about 120 samples) | residual offset ≈ 0 per minute; tactical and broadcast ball agree to a median 0.8 m |
| Ball fusion | tactical ball; gaps filled with the aligned broadcast ball (replay and close-up frames get zero weight), blended into the tactical ball at gap edges; interpolation ≤ 1 s | ball available on 59% → 63% of graded frames |
| Ball from video | YOLO26s ball detector (section 5); full-resolution detection; Viterbi tracking; a fill is used only when its track was once anchored to the tracker ball; a tactical ball is overruled when YOLO and broadcast agree against it | on held-out blocks: coverage 0.935, precision 0.826; anchored fills agree with broadcast 83% vs 2% unanchored; ball available 62% → 67% |
| Dead ball `D` | collective behaviour (calm players, no passing, ball gap, ball near a line, broadcast replay/close-up, set-piece window), anchors, two-state Viterbi, share prior 0.48 (effective playing time, Altmann et al. 2023); every segment must contain a stoppage cue | contested balls labelled `D` 1.0%; ball out ≥ 1 s labelled `D` 96.7% |
| `D` boundaries | end of `D` snapped to the restart kick, start to the ball crossing a line (± 3 s window) | IDSSE: dead F1 0.933 → 0.948; end boundary within 0.5 s: 44% → 93%; 7/7 matches |
| Whistle | two-tone whistle score from the tactical video audio; if a predicted `D` starts ≤ 3 s after a whistle heard during live play, `D` starts at the whistle | kick-off whistle found at −1.4 s (99.96th percentile); in 12 of 14 rule cases players slow down within 2 s |
| H/A model | 6 sequence models: BiGRU and two TCNs, two with a Deep-Sets encoder over the 8 nearest players of each team; 47 per-step features at 10 fps (ball, ball-local features per team, team shape, ball motion, arrival times); exact H↔A symmetry (both viewpoints averaged) | external CV ≈ 0.81 / 0.84; ghost tracks (> 11 per team, 13% of frames here) do not change the score |
| Touch evidence | 3-class kit-colour classifier (H / A / other) on person crops; touch moments from kinks in the YOLO ball path, confirmed by box contact in frames t−3…t+3; broadcast touches cover the ones the tactical camera misses | kit classifier accuracy 0.955 tactical, 0.976 broadcast; video toucher agrees with the nearest tracked player 0.90 |
| Decoder and rules | section 6 | section 7 |

## 5. Model training and data preparation

### 5.1 Data sources

| Asset | Used? | How / why not |
|---|---|---|
| Tactical ATD | **yes**, main source | player and ball positions; team per slot |
| Smart Tagging | **partly** | set-piece windows (dead-ball cue); taker team of corners, goal kicks and free kicks (checked against player geometry); kick-off after a goal. Phase tags agree with possession on only 60–76% of public frames, so they are not used |
| Tactical homography | **yes** | projecting YOLO detections to the pitch; contact checks in the image |
| Broadcast ATD + homography | **yes** | aligned ball fills tactical gaps; replay/close-up frames serve as dead-ball evidence; broadcast touches |
| Tactical video | **yes** | YOLO ball detector; touch evidence; whistle detection from audio |
| Broadcast video | **yes** | touch evidence for touches the tactical camera misses |
| Public GT (5 min) | checks only | reading the label definitions; correctness checks with bootstrap intervals |
| SkillCorner Open Data (20 matches), Metrica sample data (3) | **yes** | training data and benchmark for the possession model, decoder and every rule |
| IDSSE (Bassek et al. 2025; 7 matches, CC BY 4.0) | **validation only** | `BallStatus` validates the `D` boundaries; `BallPossession` validates the ball-out rule |
| Pretrained YOLO26x, YOLO26s, YOLO11x (COCO, Ultralytics) | **yes** | auto-labelling teacher, ball-detector initialisation, person detection |

### 5.2 Trained components and labelling

Three components have learned weights. **No training label was made by hand.** No BAR-ATH ground truth, public or
private, was used as a training label or to pick training data. The trained weights are in the repository with their
SHA-256, so a reproduction run does not retrain them.

| Component | Training data | Labels | Size | Held-out check |
|---|---|---|---|---|
| **Possession models**: 6 networks (BiGRU-set, TCN, TCN-set × seeds 0 and 1), `notebooks/pipeline/models/` | 20 SkillCorner matches (A-League, automatic broadcast tracking, 10 fps) and Metrica Sample Games 1–3 (25 fps, resampled to 10 fps), full matches; no BAR-ATH frame | the providers' event data: team of the last possession event, carried forward (SkillCorner `player_possession`; Metrica PASS, SET PIECE, SHOT, RECOVERY, BALL LOST). Masked out of the loss: dead-ball stretches (SkillCorner `game_interruption_after`; Metrica ball out, goal or foul up to the next SET PIECE) and gaps of more than 6 s after an event | 23 matches, about 6,000 possessions | 5-fold leave-match-out CV with the official spellF1 |
| **YOLO26s ball detector**, `artefak/yolo/best.pt` | 5,000 random frames (seed 0) of the BAR-ATH tactical video where the tactical and broadcast tracking balls agree within 1 m | automatic: a COCO YOLO26x teacher runs on a 640 px crop around the projected tracking ball; a label is kept only when exactly one `sports ball` (confidence ≥ 0.10) lies within 1.5 m of it. Every 5th label adds an empty negative crop | 3,907 labels: 3,230 train, 677 validation | time split (3rd of every five 60-s blocks): precision 0.997, recall 0.986, mAP50 0.995 |
| **Kit-colour classifiers** (H / A / other), one per camera: LightGBM on torso-colour features (HSV, Lab), `artefak/kit/` | BAR-ATH tactical video (every 80th graded frame) and broadcast video (every 40th aligned pitch frame); person boxes from COCO YOLO11x | automatic: each box is matched to a tracked player through the homography (Hungarian matching, unambiguous pairs only) and takes that player's team; a person on the pitch with no tracked player within 3 m is "other" (mostly referees) | tactical 41,138 crops (H 17,904 · A 18,643 · other 4,591); broadcast 41,005 (18,240 · 19,044 · 3,721) | 5-fold CV over 5-minute blocks: accuracy 0.955 tactical, 0.976 broadcast |

The ball detector and the kit classifiers are trained on the BAR-ATH videos because they must learn this match's ball,
kits and camera views, which no external dataset contains. They use frames from the whole graded match. Their labels
come only from the provided tracking and homography and from COCO-pretrained detectors, which RULES.md allows as
improving the provided data. Visual spot checks of touch-detector variants (14–16 candidates each, outside the public
window; log #80, #81, #88, #91) were used to inspect the detector and produced no labels.

### 5.3 Augmentation and training configuration

Each external match is used as four augmented copies:

- tracking noise (players σ 0.2 m, ball σ 0.4 m), random ball jumps and lost player tracks;
- **this match's ball-availability pattern**: a randomly shifted copy of the on/off mask of the BAR-ATH tracking ball,
  so the model learns to bridge the same gaps (only whether a ball position exists in each frame is used);
- half of the copies with home and away swapped.

| Setting | Value |
|---|---|
| Loss | binary cross-entropy on H vs A, live frames only; short possessions weighted more (weight ∝ duration^−0.5) |
| Optimiser | AdamW, one-cycle learning rate 2·10⁻³, weight decay 10⁻⁴, gradient clipping 1.0 |
| Schedule | 12 epochs, 40-s windows (400 steps at 10 fps), batch 32 |
| Final models | trained on all 23 matches; the CV folds are used only to measure |
| Ball detector | YOLO26s from COCO weights, 25 epochs, 640 px crops, batch 16 |
| Kit classifiers | LightGBM, 3 classes, learning rate 0.05, 31 leaves, 300 rounds |
| Software | Python 3.11, PyTorch 2.6.0 (CUDA 12.4), Ultralytics, LightGBM; versions pinned in `requirements-lock.txt` |

## 6. Inference logic

### 6.1 Temporal decoding

A three-state Viterbi decoder (H, A, D) runs at 10 fps. Its inputs are:

- the ensemble H/A log-odds (mean of the six networks, both viewpoints);
- touch evidence: each video touch adds ±β log-odds to the toucher's team until the next touch, for at most 1 s
  (β = 4 tactical, 2 broadcast ball, 0.5 broadcast candidate);
- the `D` segments, which fix the dead-ball state.

A change between H and A costs 10 (in units of ½ log-odds). The labels are then upsampled to 25 fps.

| Parameter | Value | How it was set |
|---|---|---|
| switching cost | 10 | cost curve on external CV |
| touch weights β | 4 / 2 / 0.5 | simulation on the external matches, weight following the estimated toucher accuracy |
| dead-ball share prior | 0.48 | literature (Altmann et al. 2023) |
| whistle threshold | 2.2 | audio score of clear whistles, fixed before the public check |
| restart window | 2 s | Laws of the Game (taker plays the ball first) |
| ball-out rule proximity | 1.5 m, 5 s | validated on IDSSE |

### 6.2 Possession rules

- **Dead ball `D`.** `D` starts when the ball crosses a line, or at the whistle when play stops without the ball going
  out. `D` ends at the restart kick. Forced `D` covers the graded part of the second half before kick-off and the window
  before every kick-off after a goal.
- **Change of possession.** A switch must be paid for with evidence worth the switching cost. A brief touch alone does
  not switch the team. A touch seen clearly in the video adds strong evidence and can produce a short possession when
  the model also leans that way.
- **Loose balls, aerial balls, challenges.** No evidence means no change: possession stays with the last team, as
  CHALLENGE.md states. Who wins a duel is decided by the model (positions, speeds, ball direction, arrival times) and by
  video touches. Balls in the air keep their last owner until a player of the other team touches them.
- **Restarts.** The tagged taker of a corner, goal kick or free kick owns the first 2 s after the restart. Throw-ins
  carry no team in the tags, so the decoder decides them.
- **Last touch before a corner or goal kick (ball-out rule).** If the label just before the ball goes out equals the taker's
  team R, we insert the opponents' possession from their last touch (nearest opponent ≤ 1.5 m from the ball and closer
  than any R player, within 5 s before the ball goes out) until the ball goes out. This produced 13 insertions in this
  match (median 2.1 s), none in the public window.
- **`X`.** Used only on ungraded frames; every graded frame gets H, A or D.

## 7. Experimental evaluation and results

### 7.1 Validation protocol

- **Main benchmark:** 5-fold leave-match-out CV on the 23 external matches, scored over full matches with the official
  spellF1, in three conditions: this match's ball-gap pattern (main), gaps on live play only, and ball visible.
- **Out-of-domain test:** IDSSE (7 Bundesliga matches, never trained on) for the dead-ball boundaries and the ball-out
  rule.
- **Decision rule, fixed before each run:** a component is kept only if the mean paired per-match gain is > 0 and the
  5% bootstrap lower bound over matches is > 0, without hurting any other condition.
- **Public GT:** correctness check after a decision, never used to choose.

### 7.2 Results of the final system

| Benchmark | Metric | Result |
|---|---|---|
| public GT window (5 min, check only) | spellF1 [5–95%] | **0.741 [0.577–0.882]** (official baseline 0.33 [0.21–0.45]) |
| public GT window | macroF1 · alive/dead F1 · team accuracy on live frames | 0.906 · 0.970 · 0.921 |
| public GT window | possessions predicted / true | 17 / 17 |
| external CV, 23 matches (possession model + decoder) | spellF1, BAR-ATH-style gaps / ball visible | ≈ 0.81 / ≈ 0.84 |
| IDSSE, 7 matches | dead-ball F1 | 0.948 |
| IDSSE, 7 matches | premise of the ball-out rule (last toucher ≠ taker) | 88% of corners, 83% of goal kicks |

### 7.3 Ablation study

**Component ablation.** Each row removes or replaces one component of the final system and reports the change on the
benchmark that can measure it. Negative Δ means the component helps.

| Component removed or replaced | Benchmark | With | Without | Δ |
|---|---|---|---|---|
| ensemble of the three architectures → best single architecture (TCN-set) | external CV, gaps / visible | 0.809 / 0.840 | 0.801 / 0.835 | −0.008 / −0.005 |
| sequence model → rule-based team-shape model | external CV, gaps / visible | 0.800 / 0.829 | 0.614 / 0.627 | ≈ −0.19 |
| Viterbi decoder (cost 10) → median filter / per-frame labels | external CV | ≈ 0.81 | 0.78 / 0.68 | −0.03 / −0.13 |
| video touch evidence | external CV, simulated video observer (19/23 matches) | | | −0.009 [−0.012; −0.006] |
| video touch evidence | public window | 0.741 | 0.733 | −0.008 (within noise) |
| YOLO video ball | ball available on graded frames | 67% | 62% | −5 points |
| `D` boundaries snapped to physical events | IDSSE dead-ball F1 (7/7 matches) | 0.948 | 0.933 | −0.015 |
| Laws-of-the-Game ball-out rule | IDSSE spellF1 (7/7 matches) | | | −0.0065 [−0.009; −0.004] |

The whistle rule has no spellF1 ablation, because no labelled external match has audio. Its label-free evidence is in
section 4 (kick-off whistle found at −1.4 s; players slow down within 2 s in 12 of 14 cases). On the public window
neither the whistle rule nor the ball-out rule changes the score.

**Cumulative ablation.** The system was built by adding one component at a time, each kept only after passing the
decision rule:

| Stage | Added | External CV (gaps / visible) | Public spellF1 [5–95%] | Public macroF1 |
|---|---|---|---|---|
| official baseline | nearest player + majority vote | – | 0.33 [0.21–0.45] | 0.62 |
| rule-based pipeline | rule-based `D` + team-shape model | 0.61 / 0.63 | 0.67 [0.44–0.83] | 0.89 |
| sequence ensemble | sequence models trained on 23 external matches | 0.81 / 0.84 | 0.72 [0.52–0.88] | – |
| YOLO-ball pipeline | YOLO ball + `D` snapped to physical events | ≈ 0.81 | 0.733 [0.520–0.889] | – |
| base pipeline | video touch evidence + whistle rule | + 0.009 (simulated) | 0.741 [0.577–0.882] | 0.906 |
| **final** | Laws-of-the-Game ball-out rule | IDSSE + 0.0065 (7/7) | **0.741 [0.577–0.882]** | **0.906** |

**Alternatives tested and dropped.** Each was tested with the same protocol and failed the decision rule (details in
`docs/experiment_log.md`, 110 entries):

- **training and labels:** touch-semantics labels, an extra 3-class H/A/D model, self-training, Noisy Student,
  test-time augmentation, a learned last-touch detector as input, IDSSE or the SkillCorner 2020 release as extra
  training data;
- **re-timing H↔A switches after decoding:** switches are already on time on external data (median 0.0 s);
- **smoothed-ball augmentation:** the model barely loses accuracy on smoothed balls (−0.002);
- **"nearest player owns the ball":** 0.22–0.45 alone; +0.0013 as extra evidence, not significant;
- **stacking an MLP on the model embeddings:** −0.018 [−0.024; −0.013] against soft voting;
- **decoder priors** for team dominance or per-team switching costs: within ±0.002;
- **a terminal prior** forcing the non-taker when the ball goes out, instead of the proximity insertion: −0.0045 on
  IDSSE.

### 7.4 Error analysis on the public window

This is a diagnosis, not tuning. Of 18 error episodes (25.6 s of 300 s), six account for the whole gap between 0.741
and 1.000. The three most expensive are short Barcelona touches inside Athletic possessions (0.8–1.3 s duels, or a
touch just before a free kick), where the model is confidently wrong (P(H) 0.03–0.15). The other twelve cost nothing:
switches 0.1–1.4 s early or late and slightly shifted dead-ball boundaries stay within the IoU tolerance.

## 8. Limitations and future development

- **Very short possessions in duels.** With a switching cost of 10, a 1-second possession needs an average log-odds of
  about +2 for the whole second. The model reads about −3.5 when the touching player is not tracked. A video touch adds
  +4, which is not enough, and raising its weight creates false possessions, because the touching team is right only
  about 90% of the time. *Next step:* a more precise "who touched it" signal, for example pose estimation of legs
  against the ball.
- **Throw-in takers** are not in the tags, so the ball-out rule covers corners and goal kicks only. *Next step:* infer the
  taker from player positions at the restart.
- **Stoppages without a whistle cue** (quiet whistle, ball out without a detected crossing) can start `D` 1–3 s late.
- **Aerial balls** are projected onto the ground by the homography, so their pitch position is wrong while in the air.
  *Next step:* a ball-height estimate from the two camera views.
- **Domain gap.** The model is trained on clean external tracking and sees noisier automatic tracking here. CV
  reproduces the ball-gap pattern, but not every tracking artefact. *Next step:* joint training with IDSSE, which did
  not hurt the external benchmark and was much better on IDSSE (log #76).

## 9. Reproducibility and implementation

```bash
git clone --recurse-submodules https://github.com/RayaRamadha/Mes-Que-Un-Data.git
cd Mes-Que-Un-Data
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m ipykernel install --sys-prefix --name mesqueundata
.venv\Scripts\python notebooks\pipeline\pasang_artefak.py      # installs trained YOLO / kit-colour weights
powershell -ExecutionPolicy Bypass -File run.ps1                # -> submissions/MesQueUnData.csv + official validation
```

**Data.** Match data goes in `data/tactical/` and `data/broadcast/`, including both videos. IDSSE goes in
`external_data/idsse/`; it is needed to validate the ball-out rule, or set `BALLOUT_STAGE = "force"` to apply the
validated variant without it. The repository README describes each step and its runtime.

**Model weights** (all in the repository):

| Weights | Path | Check |
|---|---|---|
| six possession models | `notebooks/pipeline/models/*.pt` | SHA-256 in `meta.json`, checked on load |
| YOLO26s ball detector | `notebooks/pipeline/artefak/yolo/best.pt` | SHA-256 matches the detection cache key |
| kit-colour classifiers | `notebooks/pipeline/artefak/kit/` | configuration keys checked on load |
| COCO YOLO26x / YOLO11x | downloaded by Ultralytics on first use | public weights |

**Runtime.** No retraining is needed. Ball detection over the whole video is recomputed on the first run, which takes
about 1.5–2 GPU hours on an RTX 3050 Ti; later runs use the cache and take minutes.

**Verification.** `run.ps1` / `run.sh` run the official `validate_submission.py` and prints the SHA-256 of the regenerated CSV,
which must equal `8ba09b17d35612bcd39e362819f75aef22c16a2416b426803e60fddf49cbacf2`. The pipeline without the ball-out rule
produced the same SHA-256 on two different computers; the ball-out rule is deterministic and needs no training. The
repository notebook, run again on 15 November 2026 with the shipped weights, regenerated this file byte for byte.

## 10. References and data sources

**Scientific references**

- Altmann et al. (2023), *Biology of Sport* 40(4): effective playing time.
- Bassek et al. (2025), *Scientific Data* 12, 195: IDSSE dataset.
- Borghesi et al. (2023), *Expert Systems with Applications* 223.
- Lea et al. (2017), *CVPR*: temporal convolutional networks.
- Zaheer et al. (2017), *NeurIPS*: Deep Sets.
- Rabiner (1989), *Proc. IEEE*: hidden Markov models; Viterbi (1967): the Viterbi algorithm.
- Jocher & Qiu (2026), *Ultralytics YOLO26*; Lin et al. (2014), *ECCV*: COCO.
- Ke et al. (2017), *NeurIPS*: LightGBM.
- Cioppa et al. (2022), *CVPRW* (SoccerNet-Tracking).
- Vidal-Codina et al. (2022), *Sports Engineering* 25.
- IFAB, *Laws of the Game*, Laws 16–17 (goal kick, corner kick).

**Data sources**

- More than a Hack 2027 repository: BAR-ATH tracking, tagging, homographies, videos and the public GT window.
- SkillCorner Open Data: github.com/SkillCorner/opendata.
- Metrica Sports sample data: github.com/metrica-sports/sample-data.
- IDSSE (CC BY 4.0): huggingface.co/datasets/pysport/idsse-data.
