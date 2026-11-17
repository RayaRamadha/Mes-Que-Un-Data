"""Schematic illustration of how the pipeline handles hard cases.

Synthetic positions only: no match data is read. Numbers in the text come from the technical report (§7).
Usage: python make_hard_cases_illustration.py OUT.mp4 [--check]  (needs matplotlib + imageio-ffmpeg)
"""
import sys
import textwrap

import imageio_ffmpeg
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FFMpegWriter  # noqa: E402
from matplotlib.patches import Arc, Circle, Rectangle  # noqa: E402

plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
plt.rcParams["font.family"] = "Segoe UI"

FPS = 25
COL = {"H": "#2563eb", "A": "#dc2626", "D": "#9ca3af"}
INK, MUTED, PITCH, LINE = "#0f172a", "#475569", "#e8f3ea", "#ffffff"
L, W = 105.0, 68.0


# ---------------------------------------------------------------- motion helpers
def path(keys, t, smooth=True):
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return np.array(keys[0][1:], float)
    if t >= ts[-1]:
        return np.array(keys[-1][1:], float)
    i = int(np.searchsorted(ts, t)) - 1
    t0, x0, y0 = keys[i]
    t1, x1, y1 = keys[i + 1]
    u = (t - t0) / (t1 - t0)
    if smooth:
        u = u * u * (3 - 2 * u)
    return np.array([x0 + (x1 - x0) * u, y0 + (y1 - y0) * u])


def label_at(segs, t):
    for a, b, lab in segs:
        if a <= t < b:
            return lab
    return None


def runs(labels, ts):
    out, s = [], 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[s]:
            out.append((ts[s], ts[i] if i < len(ts) else ts[-1] + 1 / FPS, labels[s]))
            s = i
    return out


# ---------------------------------------------------------------- scenes
SCENES = []

# 1 · ball lost by the tracker
SCENES.append(dict(
    title="Ball lost by the tracker",
    hard="The automatic tracker loses the ball on about 41% of graded frames, often during passes. A rule that "
         "follows the last known ball position hands possession to whoever runs past that spot.",
    does="Gaps are filled from the broadcast tracking and our own YOLO26 ball detector (ball available 59% → 67% "
         "of graded frames). The sequence model is trained on 23 matches with this match's own gap pattern, so "
         "it bridges what is still missing.",
    evidence="External CV with BAR-ATH-style gaps: spellF1 ≈ 0.81 · nearest-player rule alone 0.22–0.45",
    T=13.0, view=(25, 85), ycen=34,
    H={"h1": [(0, 38, 30), (3, 40, 29), (13, 42, 27)], "h2": [(0, 52, 42), (5, 56, 44), (8, 60, 46), (13, 62, 47)],
       "h3": [(0, 66, 24), (9, 68, 22), (13, 70, 22)]},
    A={"a1": [(0, 50, 30), (4, 46, 31), (13, 44, 30)], "a2": [(0, 62, 34), (13, 63, 36)],
       "a3": [(0, 72, 40), (13, 70, 40)]},
    ball=[(0, 38.8, 30), (3, 40.8, 29), (5, 56, 43.2), (8, 60.8, 45.4), (9.6, 68, 22.8), (13, 70.8, 22)],
    missing=[(4.0, 9.2)], fill=True,
    truth=[(0, 13, "H")],
    ribbons=[("Ground truth", "truth"), ("Nearest-player rule", "naive"), ("Our pipeline", [(0, 13, "H")])],
    events=[(4.0, "tracker loses the ball", None), (9.2, "tracker finds it again", None)],
))

# 2 · pass past opponents
SCENES.append(dict(
    title="A pass through a crowd",
    hard="The ball travels between opponents and team-mates without anyone touching it. Following the nearest "
         "player flips the team back and forth, so one possession is scored as seven.",
    does="Every change of team must be paid for with evidence (Viterbi decoder, switching cost 10). Being near "
         "the ball is not enough: the model also reads ball direction, speed and each team's arrival time.",
    evidence="External CV: Viterbi decoder ≈ 0.81 vs per-frame labels 0.68 vs median filter 0.78",
    T=11.0, view=(22, 82), ycen=34, slow="pass shown 3× slower",
    H={"h1": [(0, 30, 34), (11, 31, 34)], "h2": [(0, 75, 34), (11, 75.5, 34)], "h3": [(0, 47, 30.2), (11, 47.5, 30.6)],
       "h4": [(0, 57, 37.8), (11, 57.5, 37.4)]},
    A={"a1": [(0, 42, 37), (11, 43, 36.6)], "a2": [(0, 52, 31), (11, 53, 31.5)],
       "a3": [(0, 62, 37.2), (11, 63, 36.8)]},
    ball=[(0, 30.8, 34), (2, 30.8, 34), (8, 74.2, 34), (11, 74.7, 34)],
    missing=[], fill=False,
    truth=[(0, 11, "H")],
    ribbons=[("Ground truth", "truth"), ("Nearest-player rule", "naive"), ("Our pipeline", [(0, 11, "H")])],
    events=[],
))

# 3 · short interception
SCENES.append(dict(
    title="A 1-second interception in a duel",
    hard="A red player pokes the ball away and blue wins it back one second later, while the tracker has lost "
         "the ball. Positions alone still point to the team that had it before.",
    does="From both videos we find touches (a kink in the YOLO ball path + contact with a player box) and read "
         "the toucher's kit colour. A visible touch adds evidence for that team for up to 1 s, enough to open "
         "the short possession.",
    evidence="Touch evidence: +0.009 spellF1 [+0.006; +0.012], 19/23 matches (simulation) · kit classifier "
             "accuracy 0.955 tactical / 0.976 broadcast",
    T=12.0, view=(28, 78), ycen=30,
    H={"h1": [(0, 36, 30), (4, 48, 31), (6, 49, 31.5), (12, 50, 32)],
       "h2": [(0, 58, 22), (5.5, 54.6, 26.4), (12, 62, 24.5)], "h3": [(0, 44, 42), (12, 50, 44)]},
    A={"a1": [(0, 54, 34), (4.3, 49.8, 31.6), (12, 51, 30)], "a2": [(0, 62, 33), (12, 59, 28)],
       "a3": [(0, 66, 40), (12, 64, 38)]},
    ball=[(0, 36.8, 30), (4.0, 48.8, 31), (4.4, 49.2, 31.2), (5.5, 54.1, 26.8), (12, 62.8, 24.5)],
    missing=[(4.0, 5.6)], fill=False,
    truth=[(0, 4.4, "H"), (4.4, 5.5, "A"), (5.5, 12, "H")],
    ribbons=[("Ground truth", "truth"), ("Nearest-player rule", "naive"),
             ("Possession model only", [(0, 12, "H")]),
             ("+ video touch evidence", [(0, 4.5, "H"), (4.5, 5.5, "A"), (5.5, 12, "H")])],
    events=[(4.4, "touch seen in video: red kit + contact", (49.8, 31.6))],
))

# 4 · ball out and whistle
SCENES.append(dict(
    title="Ball out of play and a whistle",
    hard="Possession must stop exactly when the ball leaves the pitch or the referee stops play, and start "
         "again at the restart. The tracking keeps naming a team during stoppages.",
    does="A dead-ball detector reads collective behaviour (calm players, no passing, ball near a line, replays). "
         "Its boundaries are snapped to the ball crossing the line and to the restart; when play stops inside "
         "the pitch, D starts at the whistle heard in the audio.",
    evidence="IDSSE (7 matches, never trained on): dead-ball F1 0.933 → 0.948 · end of D within 0.5 s: 44% → 93%",
    T=16.0, view=(30, 90), ycen=54.5,
    H={"h1": [(0, 45, 55), (16, 47, 54)], "h2": [(0, 56, 50), (12.2, 51.5, 54.6), (16, 51.2, 54.2)],
       "h3": [(0, 66, 58), (4, 64, 62), (16, 62, 60)]},
    A={"a1": [(0, 70, 60), (7.5, 64, 68.6), (16, 60, 64)], "a2": [(0, 66, 52), (8.5, 60, 58), (12, 52.4, 56),
                                                                   (16, 52.5, 56.2)],
       "a3": [(0, 76, 50), (16, 72, 52)]},
    ball=[(0, 45.8, 55), (1.5, 45.8, 55), (4.0, 61.5, 68), (4.6, 63, 70.5), (8.0, 63, 70.5), (8.01, 64, 68.6),
          (8.5, 64, 68.6), (9.5, 60.6, 58.2), (12, 52.9, 55.6), (16, 52.9, 55.6)],
    missing=[], fill=False,
    truth=[(0, 4.0, "H"), (4.0, 8.5, "D"), (8.5, 12.5, "A"), (12.5, 16, "D")],
    ribbons=[("Ground truth", "truth"), ("Nearest-player rule", "naive"),
             ("Our pipeline", [(0, 4.0, "H"), (4.0, 8.5, "D"), (8.5, 12.5, "A"), (12.5, 16, "D")])],
    events=[(4.0, "ball crosses the touchline → D", (61.5, 68)), (8.5, "throw-in: play restarts", (64, 68.6)),
            (12.5, "whistle in the audio → D", (52.4, 56))],
))

# 5 · corner: who touched last
SCENES.append(dict(
    title="Corner kick: who touched the ball last?",
    hard="Red attacks until the ball goes out, so the model keeps red in possession. But a corner is only given "
         "when the defending team touched the ball last, so a short blue possession is missing.",
    does="Laws-of-the-Game rule: for corners and goal kicks, if the label before the ball goes out is the "
         "taker's team, insert the opponents' possession from their last touch (nearest opponent ≤ 1.5 m and "
         "closer than any taker, ≤ 5 s before).",
    evidence="IDSSE (7 matches, never trained on): +0.0065 spellF1, better in 7/7 matches · 13 insertions in BAR-ATH",
    T=15.0, view=(-4, 48), ycen=54,
    H={"h1": [(0, 11, 44), (4.2, 8.6, 41.6), (15, 7, 44)], "h2": [(0, 6, 50), (15, 5, 52)],
       "h3": [(0, 14, 40), (15, 12, 46)]},
    A={"a1": [(0, 24, 62), (2.4, 20, 63), (5, 18, 63), (9, 0.8, 67.2), (10, 0.8, 67.2), (15, 4, 64)],
       "a2": [(0, 16, 54), (11.5, 10.5, 47.5), (15, 10, 47)], "a3": [(0, 20, 46), (15, 16, 48)]},
    ball=[(0, 24.8, 62), (2.4, 20.8, 63), (4.2, 8.2, 41.2), (5.0, -1.5, 47), (8.5, -1.5, 47), (8.51, 0.6, 67.4),
          (10.0, 0.6, 67.4), (11.5, 10, 48), (15, 10, 47.6)],
    missing=[], fill=False,
    truth=[(0, 4.2, "A"), (4.2, 4.84, "H"), (4.84, 10, "D"), (10, 15, "A")],
    ribbons=[("Ground truth", "truth"), ("Without the rule", [(0, 4.84, "A"), (4.84, 10, "D"), (10, 15, "A")]),
             ("With the ball-out rule", [(0, 4.2, "A"), (4.2, 4.84, "H"), (4.84, 10, "D"), (10, 15, "A")])],
    events=[(4.2, "last touch: blue defender (≤ 1.5 m, closest)", (8.6, 41.6)),
            (4.84, "ball over the goal line → corner to red", (0, 46)), (10.0, "corner kick", (0.6, 67.4))],
))


def tracker_ball(sc, t):
    """ball as the tracker reports it: last known position while missing"""
    for a, b in sc["missing"]:
        if a <= t < b:
            return path(sc["ball"], a, smooth=False), False
    return path(sc["ball"], t, smooth=False), True


def naive_labels(sc):
    ts = np.arange(0, sc["T"], 1 / FPS)
    out = []
    for t in ts:
        bxy, _ = tracker_ball(sc, t)
        best = None
        for team in ("H", "A"):
            for k in sc[team].values():
                d = np.hypot(*(path(k, t) - bxy))
                if best is None or d < best[0]:
                    best = (d, team)
        out.append(best[1])
    return runs(out, ts)


for sc in SCENES:
    sc["naive"] = naive_labels(sc)


# ---------------------------------------------------------------- drawing
def draw_pitch(ax):
    ax.add_patch(Rectangle((-30, -30), L + 60, W + 60, color=PITCH, zorder=0))
    lw = 1.6
    ax.add_patch(Rectangle((0, 0), L, W, fill=False, ec=LINE, lw=lw, zorder=1))
    ax.plot([L / 2, L / 2], [0, W], color=LINE, lw=lw, zorder=1)
    ax.add_patch(Circle((L / 2, W / 2), 9.15, fill=False, ec=LINE, lw=lw, zorder=1))
    for x0, s in ((0, 1), (L, -1)):
        ax.add_patch(Rectangle((x0, W / 2 - 20.16), s * 16.5, 40.32, fill=False, ec=LINE, lw=lw, zorder=1))
        ax.add_patch(Rectangle((x0, W / 2 - 9.16), s * 5.5, 18.32, fill=False, ec=LINE, lw=lw, zorder=1))
        ax.add_patch(Rectangle((x0, W / 2 - 3.66), -s * 1.6, 7.32, fill=False, ec=LINE, lw=lw, zorder=1))
        ax.add_patch(Arc((x0 + s * 11, W / 2), 18.3, 18.3, theta1=-53 if s == 1 else 127,
                         theta2=53 if s == 1 else 233, ec=LINE, lw=lw, zorder=1))


def wrap(s, n):
    return "\n".join(textwrap.wrap(s, n))


def make_frame_fn(fig):
    state = {}

    def setup_scene(k, sc):
        fig.clf()
        fig.patch.set_facecolor("white")
        fig.text(0.03, 0.945, "Hard case {} / {} · {}".format(k + 1, len(SCENES), sc["title"]), fontsize=19,
                 fontweight="bold", color=INK)
        ax = fig.add_axes([0.03, 0.30, 0.58, 0.60])
        ax.set_aspect("equal")
        x0, x1 = sc["view"]
        h = (x1 - x0) * 0.60 * 7.2 / (0.58 * 12.8)
        ax.set_xlim(x0, x1)
        ax.set_ylim(sc["ycen"] - h / 2, sc["ycen"] + h / 2)
        ax.axis("off")
        draw_pitch(ax)
        pl = {}
        for team in ("H", "A"):
            for name in sc[team]:
                pl[(team, name)] = ax.scatter([], [], s=230, color=COL[team], edgecolor="white", lw=1.8, zorder=5)
        ball = ax.scatter([], [], s=70, color="white", edgecolor=INK, lw=1.4, zorder=7)
        ghost = ax.scatter([], [], s=150, facecolor="none", edgecolor=INK, lw=1.2, linestyle="--", zorder=6)
        ghost_t = ax.text(0, 0, "", fontsize=10, color=INK, zorder=8, ha="center", va="bottom")
        fillb = ax.scatter([], [], s=55, color="#f59e0b", edgecolor="#92400e", lw=1, zorder=7)
        fill_t = ax.text(0, 0, "", fontsize=9.5, color="#92400e", zorder=8, ha="left", va="center")
        ring = ax.scatter([], [], s=0, facecolor="none", edgecolor="#111827", lw=2.2, zorder=9)
        ev_t = ax.text(0.02, 0.04, "", transform=ax.transAxes, fontsize=12.5, fontweight="bold", color=INK,
                       zorder=10, bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cbd5e1"))
        if sc.get("slow"):
            ax.text(0.98, 0.96, sc["slow"], transform=ax.transAxes, ha="right", va="top", fontsize=10.5,
                    color=MUTED, style="italic")
        # side panel
        y = 0.885
        for head, body, colr in (("Why it is hard", sc["hard"], "#b91c1c"), ("What the pipeline does", sc["does"],
                                                                              "#047857")):
            fig.text(0.645, y, head.upper(), fontsize=10.5, fontweight="bold", color=colr)
            txt = wrap(body, 52)
            fig.text(0.645, y - 0.012, txt, fontsize=11.5, color=INK, va="top", linespacing=1.35)
            y -= 0.045 + 0.034 * (txt.count("\n") + 1)
        fig.text(0.645, y - 0.005, "EVIDENCE", fontsize=10.5, fontweight="bold", color="#1d4ed8")
        fig.text(0.645, y - 0.017, wrap(sc["evidence"], 52), fontsize=11.5, color=INK, va="top", linespacing=1.35,
                 bbox=dict(boxstyle="round,pad=0.5", fc="#eff6ff", ec="#bfdbfe"))
        # ribbons
        nr = len(sc["ribbons"])
        rb = fig.add_axes([0.20, 0.05, 0.70, 0.035 * nr + 0.02])
        rb.set_xlim(0, sc["T"])
        rb.set_ylim(-0.5, nr - 0.5)
        rb.axis("off")
        for i, (name, segs) in enumerate(sc["ribbons"]):
            segs = sc["truth"] if segs == "truth" else sc["naive"] if segs == "naive" else segs
            yy = nr - 1 - i
            for a, b, lab in segs:
                rb.add_patch(Rectangle((a, yy - 0.36), b - a, 0.72, color=COL[lab], lw=0, zorder=1))
            fig.text(0.19, rb.get_position().y0 + (yy + 0.5) / nr * rb.get_position().height, name, ha="right",
                     va="center", fontsize=11.5, color=INK, fontweight="bold" if i == nr - 1 else "normal")
            nsw = sum(1 for j in range(1, len(segs)) if {segs[j - 1][2], segs[j][2]} == {"H", "A"})
            if name != "Ground truth":
                n_poss = sum(1 for s in segs if s[2] in "HA")
                rb.text(sc["T"] * 1.003, yy, " {} poss.".format(n_poss), va="center", fontsize=9.5, color=MUTED,
                        clip_on=False)
            else:
                rb.text(sc["T"] * 1.003, yy, " {} poss.".format(sum(1 for s in segs if s[2] in "HA")),
                        va="center", fontsize=9.5, color=MUTED, clip_on=False)
        cover = Rectangle((0, -0.5), sc["T"], nr, color="white", zorder=3)
        rb.add_patch(cover)
        cur = rb.axvline(0, color=INK, lw=1.6, zorder=4)
        # legend + footer
        for i, (lab, name) in enumerate((("H", "H: home team"), ("A", "A: away team"), ("D", "D: dead ball"))):
            fig.patches.append(Rectangle((0.03 + i * 0.12, 0.022), 0.012, 0.018, transform=fig.transFigure,
                                         color=COL[lab], figure=fig))
            fig.text(0.046 + i * 0.12, 0.031, name, fontsize=10, color=MUTED, va="center")
        fig.text(0.97, 0.012, "Schematic illustration · synthetic positions, no match data · numbers from our "
                 "validation (technical report §7)", fontsize=9, color=MUTED, ha="right")
        state.update(sc=sc, ax=ax, pl=pl, ball=ball, ghost=ghost, ghost_t=ghost_t, fillb=fillb, fill_t=fill_t,
                     ring=ring, ev_t=ev_t, cover=cover, cur=cur)

    def draw(t):
        s = state
        sc = s["sc"]
        for (team, name), art in s["pl"].items():
            art.set_offsets([path(sc[team][name], t)])
        true_b = path(sc["ball"], t, smooth=False)
        tb, seen = tracker_ball(sc, t)
        if seen:
            s["ball"].set_offsets([tb])
            s["ghost"].set_offsets(np.empty((0, 2)))
            s["ghost_t"].set_text("")
            s["fillb"].set_offsets(np.empty((0, 2)))
            s["fill_t"].set_text("")
        else:
            s["ball"].set_offsets(np.empty((0, 2)))
            s["ghost"].set_offsets([tb])
            s["ghost_t"].set_position((tb[0], tb[1] + 1.8))
            s["ghost_t"].set_text("tracker: last ball")
            if sc["fill"]:
                s["fillb"].set_offsets([true_b])
                s["fill_t"].set_position((true_b[0] + 1.5, true_b[1]))
                s["fill_t"].set_text("fill: broadcast / YOLO")
            else:
                s["fillb"].set_offsets(np.empty((0, 2)))
                s["fill_t"].set_text("")
        # events
        msg, ring_xy, ring_age = "", None, None
        for te, text, xy in sc["events"]:
            if te <= t < te + 2.6:
                msg = text
                if xy is not None and t < te + 1.0:
                    ring_xy, ring_age = xy, t - te
        s["ev_t"].set_text(msg)
        s["ev_t"].set_visible(bool(msg))
        if ring_xy is not None:
            s["ring"].set_offsets([ring_xy])
            s["ring"].set_sizes([300 + 2200 * ring_age])
            s["ring"].set_alpha(1 - ring_age)
        else:
            s["ring"].set_offsets(np.empty((0, 2)))
        s["cover"].set_x(t)
        s["cover"].set_width(max(sc["T"] - t, 0))
        s["cur"].set_xdata([t, t])

    return setup_scene, draw


def card(fig, title, lines, foot=None):
    fig.clf()
    fig.patch.set_facecolor("#0f172a")
    fig.text(0.07, 0.74, title, fontsize=30, fontweight="bold", color="white")
    y = 0.62
    for big, small in lines:
        fig.text(0.07, y, big, fontsize=17, color="white", fontweight="bold")
        if small:
            fig.text(0.07, y - 0.045, small, fontsize=12.5, color="#cbd5e1")
        y -= 0.115
    if foot:
        fig.text(0.07, 0.06, foot, fontsize=11, color="#94a3b8")


INTRO = ("How the pipeline handles hard cases",
         [("Five situations where simple rules fail", "ball lost by the tracker · pass through a crowd · short "
           "interception · stoppages · corner kicks"),
          ("Each scene: the play, three or four label ribbons, and the evidence", "ribbons fill in as the play "
           "runs: blue = home (H), red = away (A), grey = dead ball (D)"),
          ("Schematic illustration", "synthetic player positions (no match data is shown, competition licence); "
           "the numbers come from our validation")],
         "Més Que Un Data · More than a Hack 2027")
OUTRO = ("What it adds up to",
         [("Public 5-minute window: spellF1 0.741 [0.577–0.882]", "official baseline 0.33 · macroF1 0.906 · "
           "17 of 17 possessions found (correctness check only)"),
          ("23 external matches, leave-match-out: spellF1 ≈ 0.81", "rule-based method 0.61 · nearest-player rule "
           "0.22–0.45"),
          ("Still hard: very short duels with an untracked toucher", "the model is confidently wrong there; a "
           "better 'who touched it' signal is the next step (technical report §8)")],
         "Més Que Un Data · full method: docs/technical_report.md · pipeline: docs/pipeline_flowchart.svg")


def main(out, check=False):
    if check:
        for i, sc in enumerate(SCENES):
            print(i + 1, sc["title"], "| naive:", [(round(a, 2), round(b, 2), l) for a, b, l in sc["naive"]])
        return
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    setup_scene, draw = make_frame_fn(fig)
    writer = FFMpegWriter(fps=FPS, codec="libx264", bitrate=3000,
                          extra_args=["-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    with writer.saving(fig, out, dpi=100):
        card(fig, *INTRO)
        for _ in range(int(6 * FPS)):
            writer.grab_frame()
        for k, sc in enumerate(SCENES):
            setup_scene(k, sc)
            draw(0.0)
            for _ in range(int(1.5 * FPS)):           # read the panel first
                writer.grab_frame()
            for t in np.arange(0, sc["T"], 1 / FPS):
                draw(t)
                writer.grab_frame()
            draw(sc["T"] - 1e-6)
            for _ in range(int(2.5 * FPS)):           # hold the finished ribbons
                writer.grab_frame()
        card(fig, *OUTRO)
        for _ in range(int(7 * FPS)):
            writer.grab_frame()
    print("written", out)


if __name__ == "__main__":
    main(sys.argv[1], check="--check" in sys.argv)
