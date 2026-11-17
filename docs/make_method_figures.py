"""Figures that show where each component of the final pipeline acts (one figure per component).

Synthetic scenes only: player and ball positions are invented, no match data is read. Each figure has four frames
from a camera view rendered from those positions, followed by the signals the component uses or produces.
Usage: python make_method_figures.py OUT_DIR [N ...]   (needs matplotlib; N = figure numbers, default all)
"""
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle  # noqa: E402

plt.rcParams["font.family"] = "Segoe UI"
plt.rcParams["font.size"] = 7

IW, IH = 1280, 720
LAB = {"H": "#2563eb", "A": "#dc2626", "D": "#9ca3af"}
KIT = {"H": ("#1d4ed8", "#f8fafc", "#1d4ed8"), "A": ("#dc2626", "#111827", "#dc2626"),
       "R": ("#111827", "#111827", "#111827"), "G": ("#16a34a", "#111827", "#16a34a")}
BOX = {"H": "#93c5fd", "A": "#fca5a5", "R": "#e5e7eb", "G": "#93c5fd"}
SRC = {"tac": "#111827", "bro": "#f59e0b", "yolo": "#a855f7"}
INK, MUTED = "#0f172a", "#64748b"


# ---------------------------------------------------------------- motion
def at(keys, t, smooth=True):
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return np.array(keys[0][1:], float)
    if t >= ts[-1]:
        return np.array(keys[-1][1:], float)
    i = int(np.searchsorted(ts, t, side="right")) - 1
    u = (t - keys[i][0]) / (keys[i + 1][0] - keys[i][0])
    if smooth:
        u = u * u * (3 - 2 * u)
    return np.array(keys[i][1:], float) * (1 - u) + np.array(keys[i + 1][1:], float) * u


def ball_at(sc, t):
    p = at(sc["ball"], t, smooth=False)
    x, y = p[:2]
    z = p[2] if len(p) > 2 else 0.0
    for t0, t1, h in sc.get("arcs", []):
        if t0 < t < t1:
            u = (t - t0) / (t1 - t0)
            z += 4 * h * u * (1 - u)
    return np.array([x, y, z])


def players_at(sc, t):
    out = []
    for team, d in sc["players"].items():
        for name, keys in d.items():
            out.append((name, team, at(keys, t)))
    return out


def nearest_team(sc, t):
    b = ball_at(sc, t)[:2]
    best = min((np.hypot(*(p - b)), team) for _, team, p in players_at(sc, t) if team in "HAG")
    return "H" if best[1] in "HG" else "A"


def runs(labels, ts, dt):
    out, s = [], 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[s]:
            out.append((ts[s], ts[i - 1] + dt, labels[s]))
            s = i
    return out


# ---------------------------------------------------------------- camera
class Cam:
    def __init__(self, pos, target, F):
        self.C = np.array(pos, float)
        f = np.array(target, float) - self.C
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, [0, 0, 1.0])
        self.r = r / np.linalg.norm(r)
        self.d = np.cross(self.f, self.r)
        self.F = F

    def proj(self, P):
        P = np.atleast_2d(np.asarray(P, float))
        if P.shape[1] == 2:
            P = np.c_[P, np.zeros(len(P))]
        p = P - self.C
        zc = p @ self.f
        return np.c_[IW / 2 + self.F * (p @ self.r) / zc, IH / 2 + self.F * (p @ self.d) / zc], zc

    def px(self, x, y, z=0.0):
        uv, zc = self.proj([[x, y, z]])
        return uv[0], zc[0]

    def scale(self, x, y):
        return self.F / self.proj([[x, y, 0]])[1][0]


def poly3(ax, cam, pts, **kw):
    uv, _ = cam.proj(pts)
    ax.add_patch(Polygon(uv, closed=True, **kw))


def line3(ax, cam, pts, **kw):
    uv, zc = cam.proj(pts)
    uv[zc <= 0.5] = np.nan
    ax.plot(uv[:, 0], uv[:, 1], **kw)


def circ_pts(cx, cy, r, a0=0, a1=2 * np.pi, n=90):
    a = np.linspace(a0, a1, n)
    return np.c_[cx + r * np.cos(a), cy + r * np.sin(a), np.zeros(n)]


STANDS = LinearSegmentedColormap.from_list("st", ["#1e293b", "#334155"])


def draw_pitch(ax, cam):
    ax.add_patch(Rectangle((0, 0), IW, IH, color="#3f8a3c", zorder=0))
    uv, zc = cam.proj([[x, 71.5, 1.0] for x in np.linspace(-25, 130, 80)])
    uv = uv[zc > 0.5]
    ax.add_patch(Polygon(np.r_[uv, [[uv[-1, 0], -5000], [uv[0, 0], -5000]]], closed=True, color="#273449",
                         zorder=0.5))
    for k in range(20):
        x0 = k * 5.25
        poly3(ax, cam, [[x0, 0, 0], [x0 + 5.25, 0, 0], [x0 + 5.25, 68, 0], [x0, 68, 0]],
              color="#4c9b47" if k % 2 else "#55a650", zorder=1, lw=0)
    poly3(ax, cam, [[-25, 71.5, 0], [130, 71.5, 0], [130, 71.5, 1.0], [-25, 71.5, 1.0]], color="#0e7490", zorder=1)
    for x in np.arange(-24, 130, 9):
        line3(ax, cam, [[x, 71.49, 0.25], [x + 4, 71.49, 0.25], [x + 4, 71.49, 0.75], [x, 71.49, 0.75],
                        [x, 71.49, 0.25]], color="#e0f2fe", lw=0.5, alpha=0.5, zorder=1)
    lk = dict(color="white", lw=1.1, alpha=0.9, zorder=2, solid_capstyle="round")
    line3(ax, cam, [[0, 0, 0], [105, 0, 0], [105, 68, 0], [0, 68, 0], [0, 0, 0]], **lk)
    line3(ax, cam, [[52.5, 0, 0], [52.5, 68, 0]], **lk)
    line3(ax, cam, circ_pts(52.5, 34, 9.15), **lk)
    for x0, s in ((0, 1), (105, -1)):
        line3(ax, cam, [[x0, 13.84, 0], [x0 + s * 16.5, 13.84, 0], [x0 + s * 16.5, 54.16, 0], [x0, 54.16, 0]], **lk)
        line3(ax, cam, [[x0, 24.84, 0], [x0 + s * 5.5, 24.84, 0], [x0 + s * 5.5, 43.16, 0], [x0, 43.16, 0]], **lk)
        a = np.arccos(5.5 / 9.15)
        cx = x0 + s * 11
        line3(ax, cam, circ_pts(cx, 34, 9.15, (-a if s == 1 else np.pi - a), (a if s == 1 else np.pi + a)), **lk)
        for c in ((0, 0), (0, 68)):
            pass
        g = x0 - s * 1.5
        net = dict(color="#e5e7eb", lw=0.6, alpha=0.7, zorder=2)
        line3(ax, cam, [[x0, 30.34, 2.44], [g, 30.34, 2.0], [g, 37.66, 2.0], [x0, 37.66, 2.44]], **net)
        line3(ax, cam, [[g, 30.34, 0], [g, 30.34, 2.0]], **net)
        line3(ax, cam, [[g, 37.66, 0], [g, 37.66, 2.0]], **net)
        line3(ax, cam, [[x0, 30.34, 0], [x0, 30.34, 2.44], [x0, 37.66, 2.44], [x0, 37.66, 0]],
              color="white", lw=1.6, zorder=3)


def draw_player(ax, cam, team, x, y, box=True, fallen=False, alpha=1.0, z=4):
    (u, v), zc = cam.px(x, y)
    s = cam.F / zc
    h, w = 1.85 * s, 0.55 * s
    shirt, shorts, socks = KIT[team]
    ax.add_patch(Ellipse((u, v), 1.3 * w, 0.28 * w, color="black", alpha=0.25 * alpha, zorder=z, lw=0))
    if fallen:
        L = 0.85 * h
        ax.add_patch(Rectangle((u - L / 2, v - 0.22 * w), 0.32 * L, 0.3 * w, color=socks, zorder=z, alpha=alpha))
        ax.add_patch(Rectangle((u - L / 2 + 0.32 * L, v - 0.25 * w), 0.2 * L, 0.36 * w, color=shorts, zorder=z,
                               alpha=alpha))
        ax.add_patch(Rectangle((u - L / 2 + 0.52 * L, v - 0.28 * w), 0.34 * L, 0.42 * w, color=shirt, zorder=z,
                               alpha=alpha))
        ax.add_patch(Circle((u + L / 2 - 0.05 * L, v - 0.08 * w), 0.09 * h, color="#d6a77a", zorder=z, alpha=alpha))
        bx = (u - L / 2 - 3, v - 0.5 * w - 3, L + 6, 0.75 * w + 6)
    else:
        for sgn in (-1, 1):
            ax.add_patch(Rectangle((u + sgn * 0.17 * w - 0.12 * w, v - 0.32 * h), 0.24 * w, 0.32 * h, color=socks,
                                   zorder=z, alpha=alpha, lw=0))
        ax.add_patch(Rectangle((u - 0.36 * w, v - 0.52 * h), 0.72 * w, 0.22 * h, color=shorts, zorder=z,
                               alpha=alpha, lw=0))
        ax.add_patch(Rectangle((u - 0.42 * w, v - 0.82 * h), 0.84 * w, 0.32 * h, color=shirt, zorder=z,
                               alpha=alpha, lw=0))
        ax.add_patch(Circle((u, v - 0.9 * h), 0.085 * h, color="#d6a77a", zorder=z, alpha=alpha, lw=0))
        bx = (u - 0.62 * w, v - 1.0 * h, 1.24 * w, 1.03 * h)
    if box:
        ax.add_patch(Rectangle(bx[:2], bx[2], bx[3], fill=False, ec=BOX[team], lw=0.8, zorder=z + 0.1,
                               alpha=alpha))
    return bx


def draw_ball(ax, cam, b, z=4, alpha=1.0):
    (gu, gv), _ = cam.px(b[0], b[1], 0)
    (u, v), zc = cam.px(*b)
    r = max(5.0, cam.F * 0.30 / zc)
    if b[2] > 0.3:
        ax.add_patch(Ellipse((gu, gv), 1.6 * r, 0.6 * r, color="black", alpha=0.3 * alpha, zorder=z, lw=0))
    ax.add_patch(Circle((u, v), r, fc="white", ec="#111827", lw=0.6, zorder=z + 0.2, alpha=alpha))
    return u, v, r


def render(ax, sc, cam, t, ball=True, boxes=True, ghost_ball=None):
    ax.set_xlim(0, IW)
    ax.set_ylim(IH, 0)
    ax.set_axis_off()
    draw_pitch(ax, cam)
    items = []
    for name, team, p in players_at(sc, t):
        zc = cam.px(*p)[1]
        items.append((zc, "p", (name, team, p)))
    b = ball_at(sc, t)
    if ball:
        items.append((cam.px(*b)[1] - 0.3, "b", b))
    items.sort(key=lambda it: -it[0])
    boxes_out, ball_px = {}, None
    for k, (zc, kind, data) in enumerate(items):
        zz = 4 + k * 0.01
        if kind == "p":
            name, team, p = data
            fallen = t >= sc.get("fallen", {}).get(name, 1e9)
            boxes_out[name] = draw_player(ax, cam, team, p[0], p[1], box=boxes, fallen=fallen, z=zz)
        else:
            ball_px = draw_ball(ax, cam, data, z=zz)
    ax.add_patch(Rectangle((0, 0), IW, IH, fill=False, ec="#0f172a", lw=0.8, zorder=50))
    return boxes_out, ball_px


# ---------------------------------------------------------------- overlay helpers
def frame_tag(ax, k, t):
    ax.add_patch(Circle((44, 44), 26, fc="white", ec="none", zorder=60))
    ax.text(44, 46, str(k), ha="center", va="center", fontsize=7, weight="bold", color=INK, zorder=61)
    ax.text(84, 46, f"t = {t:.1f} s", ha="left", va="center", fontsize=6.5, color="white", weight="bold", zorder=61,
            bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="none", alpha=0.75))


def caption(ax, text):
    ax.text(18, IH - 20, text, ha="left", va="bottom", fontsize=6, color="white", zorder=61,
            bbox=dict(boxstyle="round,pad=0.25", fc="#0f172a", ec="none", alpha=0.75))


def call(ax, text, xy, xytext, color="white", fc="#0f172a"):
    half = 10.5 * len(text) + 20
    xytext = (min(max(xytext[0], half + 10), IW - half - 10), min(max(xytext[1], 95), IH - 70))
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=5.6, color=color, ha="center", va="center", zorder=62,
                bbox=dict(boxstyle="round,pad=0.2", fc=fc, ec="none", alpha=0.82),
                arrowprops=dict(arrowstyle="-", color=fc if fc != "#0f172a" else "white", lw=0.7, alpha=0.9))


def ground_ring(ax, cam, x, y, r, color, lw=1.0, ls="-", fill=None):
    uv, _ = cam.proj(circ_pts(x, y, r))
    if fill:
        ax.add_patch(Polygon(uv, closed=True, fc=fill, ec="none", alpha=0.3, zorder=3))
    ax.plot(uv[:, 0], uv[:, 1], color=color, lw=lw, ls=ls, zorder=3.5)


def ground_arrow(ax, cam, p0, p1, color, lw=1.0, z=3.6):
    a, _ = cam.px(*p0)
    b, _ = cam.px(*p1)
    ax.annotate("", xy=b, xytext=a, zorder=z,
                arrowprops=dict(arrowstyle="-|>,head_width=0.18,head_length=0.35", color=color, lw=lw))


def box_px(ax, u, v, half, color, label=None, lw=1.1):
    ax.add_patch(Rectangle((u - half, v - half), 2 * half, 2 * half, fill=False, ec=color, lw=lw, zorder=63))
    if label:
        ax.text(u - half, v - half - 3, label, fontsize=5.4, color="white", ha="left", va="bottom", zorder=63,
                bbox=dict(boxstyle="square,pad=0.15", fc=color, ec="none"))


# ---------------------------------------------------------------- strip helpers
def ribbon(ax, segs, label, T):
    ax.set_xlim(0, T)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    for a, b, lab in segs:
        ax.add_patch(Rectangle((a, 0.05), b - a, 0.6, fc=LAB[lab], ec="white", lw=0.6))
        if b - a > 0.035 * T:
            ax.text((a + b) / 2, 0.35, lab, ha="center", va="center", fontsize=6.3, color="white", weight="bold")
    ax.text(0, 0.8, label, ha="left", va="center", fontsize=6.6, color=INK)
    for s in ax.spines.values():
        s.set_visible(False)


def source_bar(ax, segs, label, T, right=None):
    ax.set_xlim(0, T)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.add_patch(Rectangle((0, 0.15), T, 0.4, fc="#f1f5f9", ec="none"))
    for a, b, src in segs:
        ax.add_patch(Rectangle((a, 0.15), b - a, 0.4, fc=SRC[src], ec="none"))
    ax.text(0, 0.8, label, ha="left", va="center", fontsize=6.6, color=INK)
    if right:
        ax.text(T, 0.8, right, ha="right", va="center", fontsize=6.2, color=MUTED)
    for s in ax.spines.values():
        s.set_visible(False)


def curve_axes(ax, T, label, ylim, yticks):
    ax.set_xlim(0, T)
    ax.set_ylim(*ylim)
    ax.set_yticks(yticks)
    ax.tick_params(labelsize=6, length=2, pad=1)
    ax.text(0.003, 0.97, label, transform=ax.transAxes, ha="left", va="top", fontsize=6.6, color=INK,
            bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.5))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#cbd5e1")


# ---------------------------------------------------------------- figure layout
def build(spec, out):
    T = spec["T"]
    rows = spec["strip"]
    Wf, L, R, G = 10.0, 0.3, 0.12, 0.06
    pw = (Wf - L - R - 3 * G) / 4
    ph = pw * IH / IW
    hs = [0.33 if r[0] in ("ribbon", "source") else 0.74 for r in rows]
    gap = 0.07
    Hf = 0.06 + ph + 0.22 + sum(hs) + gap * (len(rows) - 1) + 0.36
    fig = plt.figure(figsize=(Wf, Hf), dpi=220)
    fig.patch.set_facecolor("white")
    top = Hf - 0.06
    for k, (t, cap) in enumerate(spec["frames"]):
        ax = fig.add_axes([(L + k * (pw + G)) / Wf, (top - ph) / Hf, pw / Wf, ph / Hf])
        sc = spec["scene"]
        boxes, ball_px = render(ax, sc, spec["cam"], t, ball=spec.get("show_ball", lambda t: True)(t))
        spec["overlay"](ax, spec["cam"], t, k, boxes, ball_px)
        frame_tag(ax, k + 1, t)
        caption(ax, cap)
    fig.text(0.12 / Wf, (top - ph / 2) / Hf, "Camera view (synthetic)", rotation=90, ha="center", va="center",
             fontsize=6.6, color=MUTED)
    y = top - ph - 0.22
    axes = []
    for i, (row, h) in enumerate(zip(rows, hs)):
        y -= h
        ax = fig.add_axes([L / Wf, y / Hf, (Wf - L - R) / Wf, h / Hf])
        axes.append(ax)
        kind = row[0]
        if kind == "ribbon":
            ribbon(ax, row[2], row[1], T)
        elif kind == "source":
            source_bar(ax, row[2], row[1], T, row[3] if len(row) > 3 else None)
        else:
            row[1](ax)
        marks = {}
        for k, (t, _) in enumerate(spec["frames"]):
            marks.setdefault(t, []).append(str(k + 1))
        for t, ks in marks.items():
            ax.axvline(t, color="#94a3b8", lw=0.6, ls=(0, (2, 2)), zorder=0.5)
            if i == 0:
                ax.annotate("·".join(ks), xy=(t, 1), xycoords=("data", "axes fraction"), xytext=(0, 7),
                            textcoords="offset points", ha="center", va="center", fontsize=6.2, weight="bold",
                            color=INK, bbox=dict(boxstyle="round,pad=0.2", fc="#e2e8f0", ec="none"))
        if i < len(rows) - 1:
            ax.set_xticks([])
        else:
            ax.set_xticks(np.arange(0, T + 0.01, 1 if T <= 16 else 2))
            ax.tick_params(axis="x", labelsize=6, length=2, pad=1)
            ax.set_xlabel("time (s)", fontsize=6.6, labelpad=1, color=MUTED)
            ax.spines["bottom"].set_visible(True)
            ax.spines["bottom"].set_color("#cbd5e1")
        y -= gap
    fig.savefig(out, dpi=220, facecolor="white")
    plt.close(fig)


# ================================================================ 1 · ball fusion
def fig_ball():
    T = 10.0
    sc = dict(players={
        "H": {"h1": [(0, 39, 30), (2.6, 40.5, 29.6), (10, 43, 29)], "h2": [(0, 59, 43), (6.6, 64.2, 45.2),
                                                                            (10, 67.5, 46)],
              "h3": [(0, 51, 20), (10, 56, 21)], "h4": [(0, 45, 44), (10, 50, 45)]},
        "A": {"a1": [(0, 49, 32), (4, 46, 31), (10, 45, 31)], "a2": [(0, 61, 36), (10, 64, 39.5)],
              "a3": [(0, 69, 40), (10, 70, 42)], "a4": [(0, 57, 27), (10, 59, 29)]},
        "R": {"r": [(0, 53, 37), (10, 58, 37)]}},
        ball=[(0, 39.8, 30.2, 0), (2.6, 41.3, 29.8, 0), (6.6, 64.4, 44.6, 0), (10, 68.3, 46.1, 0)],
        arcs=[(2.6, 6.6, 4.0)])
    cam = Cam((54, -12, 16), (54, 36, 0), 1900)
    tac = [(0, 3.0, "tac"), (7.6, 10, "tac")]
    bro = [(3.0, 4.8, "bro")]
    yol = [(4.8, 7.6, "yolo")]
    last = ball_at(sc, 3.0)

    def overlay(ax, cam, t, k, boxes, bp):
        segs = [(0, 3.0, "tac"), (3.0, 4.8, "bro"), (4.8, 7.6, "yolo"), (7.6, 10, "tac")]
        for a, b_, s in segs:
            ts = np.linspace(a, min(b_, t), 25)
            if ts[-1] <= a:
                continue
            uv, _ = cam.proj(np.array([ball_at(sc, tt) * [1, 1, 0] for tt in ts]))
            ax.plot(uv[:, 0], uv[:, 1], color=SRC[s], lw=1.6, alpha=0.9, zorder=3.4)
        u, v, r = bp
        if k in (1, 2):
            (gu, gv), _ = cam.px(*last)
            ax.plot(gu, gv, marker="x", color="#e5e7eb", ms=6, mew=1.2, zorder=63)
            call(ax, "last tracker position", (gu, gv), (gu - 40, gv + 120))
        if k in (0, 3):
            ax.plot([u - 3 * r, u + 3 * r], [v, v], color=SRC["tac"], lw=1.0, zorder=63)
            ax.plot([u, u], [v - 3 * r, v + 3 * r], color=SRC["tac"], lw=1.0, zorder=63)
            call(ax, "tracker ball", (u, v), (u + 150, v - 110))
        if k == 1:
            ax.add_patch(Circle((u, v), 3 * r, fill=False, ec=SRC["bro"], lw=1.6, zorder=63))
            call(ax, "broadcast ball, aligned in time", (u, v), (u + 60, v - 150), fc=SRC["bro"], color=INK)
        if k == 2:
            box_px(ax, u, v, 3 * r, SRC["yolo"], "ball 0.86")
            call(ax, "YOLO26s detection", (u, v + 3 * r), (u - 60, v + 170), fc=SRC["yolo"])

    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(2.2, "tracker ball present"), (3.9, "tracker gap: broadcast fill"),
                        (5.9, "tracker gap: YOLO fill"), (8.4, "tracker ball back")],
                strip=[("source", "Tactical tracker ball", tac),
                       ("source", "Broadcast ball, aligned per half (fills gaps)", bro),
                       ("source", "YOLO26s ball from the video (anchored fills)", yol),
                       ("source", "Fused ball used by every later stage", tac + bro + yol)])


# ================================================================ 2 · dead ball
def fig_dead():
    T = 15.0
    sc = dict(players={
        "H": {"h1": [(0, 38, 9), (3.6, 45.5, 6.5), (5, 46.5, 7.5), (15, 47, 9)],
              "h3": [(0, 40, 18), (4, 43, 14), (9.6, 46.4, -0.6), (11.2, 46.2, -0.4), (15, 46.6, 3)],
              "h4": [(0, 48, 22), (5, 51, 17), (11, 52, 12), (15, 54, 11)], "h5": [(0, 33, 22), (15, 38, 20)]},
        "A": {"a1": [(0, 52, 10), (3.6, 46.6, 6.2), (6, 47.8, 7.8), (15, 49, 10)],
              "a2": [(0, 55, 18), (6, 52, 15), (15, 51.5, 14)], "a3": [(0, 44, 25), (15, 47, 21)]},
        "R": {"r": [(0, 45, 30), (4, 47, 25), (15, 49, 22)]}},
        ball=[(0, 38.8, 8.6, 0), (3.5, 45.2, 6.0, 0), (3.6, 45.6, 5.8, 0), (4.0, 46.6, 0.0, 0),
              (4.8, 47.2, -3.0, 0), (6.0, 47.0, -3.4, 0), (9.6, 46.6, -1.2, 0), (11.0, 46.4, -0.8, 2.0),
              (12.0, 49.0, 7.0, 0), (15, 52, 9, 0)],
        arcs=[(11.0, 12.0, 0.8)])
    sc["ball"][-3] = (11.0, 46.4, -0.8, 2.0)
    cam = Cam((47, -30, 13), (47, 8, 0), 2000)

    def speed(t):
        return 0.8 + 3.6 / (1 + np.exp((t - 5.4) * 2.2)) + 3.0 / (1 + np.exp(-(t - 11.4) * 3))

    def score(t):
        return 0.04 + 0.9 / (1 + np.exp(-(t - 5.6) * 2.6)) - 0.9 / (1 + np.exp(-(t - 10.0) * 3.2))

    def overlay(ax, cam, t, k, boxes, bp):
        u, v, r = bp
        if k == 0:
            for name, team, p in players_at(sc, t):
                p2 = players_at(sc, t + 0.6)
                q = [pp for nn, _, pp in p2 if nn == name][0]
                ground_arrow(ax, cam, (p[0], p[1], 0), (q[0] + (q[0] - p[0]) * 1.5, q[1] + (q[1] - p[1]) * 1.5, 0),
                             "#fef08a", lw=0.9)
            call(ax, "players run, ball in play", (u, v), (u - 120, v - 230))
        if k == 1:
            line3(ax, cam, [[36, 0, 0], [58, 0, 0]], color="#facc15", lw=2.2, zorder=3.6)
            call(ax, "ball crosses the line: D starts here", (u, v), (u + 40, v - 250), fc="#facc15", color=INK)
        if k == 2:
            call(ax, "calm players · no passing · ball off the pitch", (u, v), (u + 20, v - 300))
        if k == 3:
            call(ax, "restart (throw-in): D ends here", (u, v), (u + 60, v - 260), fc="#facc15", color=INK)

    def c1(ax):
        tt = np.linspace(0, T, 400)
        curve_axes(ax, T, "Cue: mean player speed (m/s)", (0, 5.2), [0, 2, 4])
        ax.plot(tt, speed(tt), color=INK, lw=1.1)

    def c2(ax):
        tt = np.linspace(0, T, 400)
        curve_axes(ax, T, "Dead-ball score (two-state Viterbi input)", (0, 1.05), [0, 0.5, 1])
        ax.plot(tt, score(tt), color=LAB["D"], lw=1.4)
        ax.axhline(0.5, color=MUTED, lw=0.6, ls="--")

    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(3.2, "live play"), (4.0, "ball out: start snapped"), (7.5, "stoppage"),
                        (11.0, "restart: end snapped")],
                strip=[("curve", c1), ("curve", c2),
                       ("ribbon", "Detector segment before snapping", [(0, 5.4, "H"), (5.4, 10.2, "D"),
                                                                       (10.2, T, "H")]),
                       ("ribbon", "After boundary snapping (line crossing → restart)",
                        [(0, 4.0, "H"), (4.0, 11.0, "D"), (11.0, T, "H")])])


# ================================================================ 3 · possession model
def fig_model():
    T = 12.0
    sc = dict(players={
        "H": {"h1": [(0, 40, 24), (6.5, 50, 28), (12, 52, 29)], "h2": [(0, 46, 40), (12, 54, 42)],
              "h3": [(0, 56, 18), (7.5, 60, 20), (12, 58, 24)], "h4": [(0, 34, 34), (12, 42, 36)],
              "h5": [(0, 60, 44), (12, 64, 44)]},
        "A": {"a1": [(0, 52, 30), (6.5, 53, 28.5), (12, 51, 29)], "a2": [(0, 61, 28), (7.3, 56.4, 23.7),
                                                                       (12, 66, 28)],
              "a3": [(0, 48, 18), (12, 55, 19)], "a4": [(0, 58, 37), (12, 63, 36)],
              "a5": [(0, 66, 24), (12, 70, 27)]},
        "R": {"r": [(0, 50, 46), (12, 56, 44)]}},
        ball=[(0, 40.8, 24.3, 0), (6.5, 50.7, 27.9, 0), (7.3, 56.0, 24.0, 0), (12, 66.6, 27.6, 0)])
    cam = Cam((51, -8, 15), (51, 32, 0), 1750)
    rng = np.random.default_rng(3)
    tt = np.arange(0, T, 0.1)
    base = np.where(tt < 7.3, 2.6 - 1.4 * np.clip((tt - 4.5) / 2.8, 0, 1), -2.8 + 0.8 * np.exp(-(tt - 7.3)))
    base = np.convolve(np.r_[np.full(3, base[0]), base, np.full(3, base[-1])], np.ones(7) / 7, "valid")
    nets = [base + np.cumsum(rng.normal(0, 0.08, len(tt))) * 0.5 + rng.normal(0, 0.25) for _ in range(6)]

    def arrival(team, t):
        b = ball_at(sc, t)[:2]
        return min(np.hypot(*(p - b)) / 7.0 + 0.25 for _, tm, p in players_at(sc, t) if tm == team)

    def overlay(ax, cam, t, k, boxes, bp):
        u, v, r = bp
        b = ball_at(sc, t)
        if k == 0:
            pl = players_at(sc, t)
            for team in "HA":
                ps = sorted([p for _, tm, p in pl if tm == team], key=lambda p: np.hypot(*(p - b[:2])))[:4]
                for p in ps:
                    line3(ax, cam, [[b[0], b[1], 0], [p[0], p[1], 0]], color=BOX[team], lw=0.9, zorder=3.6)
            call(ax, "nearest players of each team (set encoder)", (u, v), (u, v - 280))
        if k == 1:
            for team in "HA":
                pts = np.array([p for _, tm, p in players_at(sc, t) if tm == team])
                c = pts.mean(0)
                order = np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))
                hull = np.c_[pts[order], np.zeros(len(pts))]
                uv, _ = cam.proj(hull)
                ax.add_patch(Polygon(uv, closed=True, fc=LAB[team], ec=LAB[team], alpha=0.22, lw=1, zorder=3.3))
            call(ax, "team shape", (u, v), (u - 160, v - 250))
        if k == 2:
            b2 = ball_at(sc, t + 0.5)
            ground_arrow(ax, cam, (b[0], b[1], 0), (b[0] + (b2[0] - b[0]) * 2, b[1] + (b2[1] - b[1]) * 2, 0),
                         "#fef08a", lw=1.4)
            ah, aa = arrival("H", t), arrival("A", t)
            call(ax, f"ball direction & speed · arrival time: red {aa:.1f} s, blue {ah:.1f} s", (u, v),
                 (u - 30, v - 290))
        if k == 3:
            call(ax, "red carries: log-odds below 0", (u, v), (u - 140, v - 260), fc=LAB["A"])

    def c1(ax):
        curve_axes(ax, T, "First arrival at the ball (s): blue / red", (0, 3.2), [0, 1, 2, 3])
        ts = np.linspace(0, T, 300)
        ax.plot(ts, [arrival("H", t) for t in ts], color=LAB["H"], lw=1.1)
        ax.plot(ts, [arrival("A", t) for t in ts], color=LAB["A"], lw=1.1)

    def c2(ax):
        curve_axes(ax, T, "H/A log-odds: six networks (thin) and their mean", (-4.2, 4.2), [-4, 0, 4])
        for n in nets:
            ax.plot(tt, n, color="#94a3b8", lw=0.5)
        m = np.mean(nets, 0)
        ax.plot(tt, m, color=INK, lw=1.3)
        ax.fill_between(tt, 0, m, where=m > 0, color=LAB["H"], alpha=0.15, lw=0)
        ax.fill_between(tt, 0, m, where=m < 0, color=LAB["A"], alpha=0.15, lw=0)
        ax.axhline(0, color=MUTED, lw=0.6)

    m = np.mean(nets, 0)
    lab = ["H" if x > 0 else "A" for x in m]
    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(2.0, "47 features per step, 10 fps"), (5.0, "team shape"), (6.9, "pass: arrival times"),
                        (9.5, "interception")],
                strip=[("curve", c1), ("curve", c2), ("ribbon", "Sign of the ensemble mean", runs(lab, tt, 0.1))])


# ================================================================ 4 · touch evidence
def fig_touch():
    T = 10.0
    sc = dict(players={
        "H": {"h1": [(0, 38, 30), (4.3, 48, 31), (6, 49, 31.5), (10, 50, 32)],
              "h2": [(0, 58, 22), (5.5, 54.6, 26.4), (10, 61, 25)], "h3": [(0, 42, 41), (10, 47, 43)]},
        "A": {"a1": [(0, 55, 34), (4.3, 49.8, 31.9), (10, 51, 30)], "a2": [(0, 62, 33), (10, 59, 28)],
              "a3": [(0, 64, 40), (10, 63, 38)]},
        "R": {"r": [(0, 46, 20), (10, 52, 22)]}},
        ball=[(0, 38.8, 30, 0), (4.0, 48.6, 31, 0), (4.4, 49.3, 31.3, 0), (5.5, 54.1, 26.8, 0),
              (10, 61.8, 25, 0)])
    cam = Cam((51, 1, 12), (51, 31, 0), 2300)
    tt = np.arange(0, T, 0.1)
    model = 2.4 - 1.7 * np.exp(-((tt - 4.9) / 0.8) ** 2)
    ev = np.where((tt >= 4.4) & (tt < 5.4), -4.0, 0) + np.where((tt >= 5.5) & (tt < 6.5), 4.0, 0)

    def overlay(ax, cam, t, k, boxes, bp):
        u, v, r = bp
        if k == 1:
            ts = np.linspace(3.5, 5.3, 19)
            uv, _ = cam.proj([ball_at(sc, x) for x in ts])
            ax.plot(uv[:, 0], uv[:, 1], ".", color=SRC["yolo"], ms=3.2, zorder=63)
            (ku, kv), _ = cam.px(*ball_at(sc, 4.4))
            ax.add_patch(Circle((ku, kv), 34, fill=False, ec="#facc15", lw=1.4, zorder=63))
            call(ax, "kink in the YOLO ball path", (ku, kv), (ku + 230, kv + 120), fc="#facc15", color=INK)
            bx = boxes["a1"]
            ax.add_patch(Rectangle(bx[:2], bx[2], bx[3], fill=False, ec="#facc15", lw=1.4, zorder=63))
            call(ax, "ball touches a player box (t−3 … t+3)", (bx[0] + bx[2] / 2, bx[1]),
                 (bx[0] + bx[2] / 2 - 40, bx[1] - 110))
        if k == 2:
            bx = boxes["a1"]
            ax.add_patch(Rectangle(bx[:2], bx[2], bx[3], fill=False, ec="#facc15", lw=1.4, zorder=63))
            ins = ax.inset_axes([0.62, 0.08, 0.34, 0.6])
            ins.set_xlim(bx[0] - 6, bx[0] + bx[2] + 6)
            ins.set_ylim(bx[1] + bx[3] + 6, bx[1] - 6)
            draw_pitch(ins, cam)
            draw_player(ins, cam, "A", *at(sc["players"]["A"]["a1"], t), box=False)
            draw_player(ins, cam, "H", *at(sc["players"]["H"]["h1"], t), box=False, alpha=0.5)
            ins.set_xticks([])
            ins.set_yticks([])
            for s in ins.spines.values():
                s.set_color("#facc15")
                s.set_linewidth(1.2)
            ax.text(0.79, 0.71, "kit colour: A 0.96 · H 0.03", transform=ax.transAxes, ha="center", va="bottom",
                    fontsize=5.6, color="white", zorder=64,
                    bbox=dict(boxstyle="round,pad=0.2", fc=LAB["A"], ec="none"))
            ax.annotate("", xy=(0.62, 0.38), xycoords="axes fraction", xytext=(bx[0] + bx[2], bx[1] + bx[3] / 2),
                        textcoords="data", arrowprops=dict(arrowstyle="-", color="#facc15", lw=0.8), zorder=63)
        if k == 3:
            bx = boxes["h2"]
            ax.add_patch(Rectangle(bx[:2], bx[2], bx[3], fill=False, ec="#facc15", lw=1.4, zorder=63))
            call(ax, "touch by blue kit → evidence for H", (bx[0] + bx[2] / 2, bx[1]),
                 (bx[0] + bx[2] / 2 + 60, bx[1] - 120), fc=LAB["H"])

    def c1(ax):
        curve_axes(ax, T, "Touch evidence ±β (β = 4 tactical camera; at most 1 s)", (-4.8, 4.8), [-4, 0, 4])
        ax.fill_between(tt, 0, ev, step="post", color=LAB["A"], alpha=0.5, where=ev < 0, lw=0)
        ax.fill_between(tt, 0, ev, step="post", color=LAB["H"], alpha=0.5, where=ev > 0, lw=0)
        ax.axhline(0, color=MUTED, lw=0.6)

    def c2(ax):
        curve_axes(ax, T, "H/A log-odds: model only (grey) and with touch evidence (black)", (-3.5, 7.5), [-2, 0, 2, 4, 6])
        ax.plot(tt, model, color="#94a3b8", lw=1.2)
        ax.plot(tt, model + ev, color=INK, lw=1.2, drawstyle="steps-post")
        ax.axhline(0, color=MUTED, lw=0.6)

    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(3.6, "duel, tracker ball lost"), (4.4, "touch detected"), (4.4, "toucher's kit colour"),
                        (5.5, "blue wins it back")],
                strip=[("curve", c1), ("curve", c2), ("ribbon", "Decoded without touch evidence", [(0, T, "H")]),
                       ("ribbon", "Decoded with touch evidence",
                        [(0, 4.5, "H"), (4.5, 5.5, "A"), (5.5, T, "H")])])


# ================================================================ 5 · Viterbi decoder
def fig_viterbi():
    T = 5.0
    sc = dict(players={
        "H": {"h1": [(0, 36, 34), (7, 37, 34)], "h2": [(0, 70, 34), (7, 70.5, 34)],
              "h3": [(0, 49, 31.0), (7, 49.4, 31.3)], "h4": [(0, 57.5, 37.2), (7, 57.8, 37.0)]},
        "A": {"a1": [(0, 44, 36.6), (7, 44.6, 36.3)], "a2": [(0, 53, 31.4), (7, 53.6, 31.7)],
              "a3": [(0, 62, 36.8), (7, 62.7, 36.5)]},
        "R": {"r": [(0, 52, 44), (7, 54, 44)]}},
        ball=[(0, 36.8, 34, 0), (1.5, 36.8, 34, 0), (4.0, 69.2, 34, 0), (7, 69.7, 34, 0)])
    cam = Cam((53, 0, 14), (53, 34, 0), 1750)
    dt = 0.04
    ts = np.arange(0, T, dt)
    naive = [nearest_team(sc, t) for t in ts]
    rn = runs(naive, ts, dt)
    mid = [round((x + y) / 2, 1) for x, y, _ in rn]
    t10 = np.arange(0, T, 0.1)
    lo = 1.6 - 2.3 * np.exp(-((t10 - mid[1]) / 0.2) ** 2) - 2.7 * np.exp(-((t10 - mid[3]) / 0.18) ** 2)
    lo += 0.25 * np.sin(t10 * 5.1)
    frame = ["H" if x > 0 else "A" for x in lo]

    def overlay(ax, cam, t, k, boxes, bp):
        u, v, r = bp
        nt = nearest_team(sc, t)
        b = ball_at(sc, t)
        pl = [(np.hypot(*(p - b[:2])), n, tm, p) for n, tm, p in players_at(sc, t) if tm in "HA"]
        d, n, tm, p = min(pl)
        line3(ax, cam, [[b[0], b[1], 0], [p[0], p[1], 0]], color="#facc15", lw=1.4, zorder=3.6)
        call(ax, f"nearest player: {'blue' if nt == 'H' else 'red'} · no touch", (u, v), (u, v - 210),
             fc=LAB[nt])

    def c1(ax):
        curve_axes(ax, T, "H/A log-odds per step (10 fps)", (-2.2, 2.4), [-2, 0, 2])
        ax.plot(t10, lo, color=INK, lw=1.1)
        ax.fill_between(t10, 0, lo, where=lo < 0, color=LAB["A"], alpha=0.3, lw=0)
        ax.axhline(0, color=MUTED, lw=0.6)
        ax.text(T * 0.985, -1.75, "each red dip is worth less than the two switches it would need (2 × 10)",
                ha="right", va="center", fontsize=6, color=MUTED)

    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(1.0, "pass starts"), (mid[1], "ball passes red"), (mid[2], "ball passes blue"),
                        (mid[3], "ball passes red")],
                strip=[("curve", c1), ("ribbon", "Nearest player at each frame", rn),
                       ("ribbon", "Sign of the log-odds at each step", runs(frame, t10, 0.1)),
                       ("ribbon", "Three-state Viterbi decoder (switch cost 10)", [(0, T, "H")])])


# ================================================================ 6 · whistle
def fig_whistle():
    T = 13.0
    sc = dict(players={
        "H": {"h1": [(0, 52, 29), (5.0, 60, 30.5), (13, 60, 30.5)],
              "h2": [(0, 48, 38), (5, 54, 37), (8, 58.5, 32), (10.6, 59.6, 31.0), (13, 61, 33)],
              "h3": [(0, 60, 20), (13, 68, 24)], "h4": [(0, 45, 24), (13, 52, 25)]},
        "A": {"a1": [(0, 66, 34), (5.0, 61, 31), (6.5, 62, 32), (13, 63, 33)],
              "a2": [(0, 70, 26), (6, 66, 27), (13, 66, 27.5)], "a3": [(0, 68, 42), (6, 65, 38), (13, 64, 37)]},
        "R": {"r": [(0, 55, 42), (5.3, 59, 38), (8, 60, 36.5), (13, 60.5, 36.5)]}},
        ball=[(0, 52.8, 29.3, 0), (4.9, 60.6, 30.5, 0), (5.5, 62.3, 30.0, 0), (10.6, 60.6, 30.4, 0),
              (10.8, 60.8, 30.4, 0), (12.0, 67.5, 24.5, 0), (13, 68, 24, 0)],
        fallen={"h1": 5.05})
    sc["ball"][3] = (10.6, 60.4, 30.6, 0)
    cam = Cam((61, -4, 13), (61, 32, 0), 1950)
    tt = np.linspace(0, T, 1300)
    rng = np.random.default_rng(1)
    whistle = 0.6 + 0.25 * rng.random(len(tt)) + 2.6 * np.exp(-((tt - 5.35) / 0.12) ** 2)

    def overlay(ax, cam, t, k, boxes, bp):
        u, v, r = bp
        if k == 0:
            call(ax, "tackle during live play", (u, v), (u - 120, v - 250))
        if k == 1:
            bx = boxes["r"]
            cx, cy = bx[0] + bx[2] / 2, bx[1]
            for rr in (18, 30, 42):
                ax.add_patch(matplotlib.patches.Arc((cx, cy - 10), 2 * rr, 2 * rr, theta1=20, theta2=160,
                                                    color="#facc15", lw=1.1, zorder=63))
            call(ax, "whistle in the audio (score 3.2 > 2.2)", (cx, cy - 30), (cx - 40, cy - 150), fc="#facc15",
                 color=INK)
        if k == 2:
            call(ax, "players slow down within 2 s", (u, v), (u - 80, v - 260))
        if k == 3:
            call(ax, "free kick: tagged taker team owns the first 2 s", (u, v), (u - 120, v - 260))

    def c1(ax):
        curve_axes(ax, T, "Two-tone whistle score from the tactical-video audio", (0, 4), [0, 2.2])
        ax.plot(tt, whistle, color=INK, lw=0.8)
        ax.axhline(2.2, color="#d97706", lw=0.7, ls="--")
        ax.text(T * 0.995, 2.35, "threshold 2.2", ha="right", va="bottom", fontsize=6, color="#d97706")

    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(4.9, "duel"), (5.3, "whistle"), (7.5, "stoppage"), (10.8, "restart")],
                strip=[("curve", c1),
                       ("ribbon", "Dead-ball detector (D starts when players stop)",
                        [(0, 7.4, "H"), (7.4, 10.8, "D"), (10.8, T, "H")]),
                       ("ribbon", "Whistle rule: D ≤ 3 s after a whistle starts at the whistle",
                        [(0, 5.35, "H"), (5.35, 10.8, "D"), (10.8, T, "H")])])


# ================================================================ 7 · ball-out rule
def fig_ballout():
    T = 10.0
    sc = dict(players={
        "H": {"h1": [(0, 96.5, 30), (4.2, 98.6, 30.8), (10, 99, 30)], "h2": [(0, 98, 37), (10, 99, 35)],
              "h3": [(0, 95, 23), (4, 97, 24), (10, 98, 22)], "h4": [(0, 88, 32), (10, 92, 30)]},
        "G": {"gk": [(0, 103.5, 34), (4.5, 103.2, 32), (10, 103.5, 31)]},
        "A": {"a1": [(0, 86, 8), (3.0, 92, 6), (6, 99, 2.5), (8.2, 104.6, 0.4), (10, 103, 2)],
              "a2": [(0, 94, 38), (4.2, 97.5, 33.5), (10, 98, 33)],
              "a3": [(0, 92, 27), (4.2, 96.8, 28), (10, 97, 27)], "a4": [(0, 85, 22), (10, 90, 24)]},
        "R": {"r": [(0, 82, 28), (10, 87, 24)]}},
        ball=[(0, 86.6, 8.4, 0), (3.0, 92.6, 6.4, 0), (4.2, 98.6, 30.8, 2.3), (4.84, 105.0, 24.5, 1.0),
              (5.6, 108, 22, 0), (7.6, 106, 8, 0), (8.2, 104.9, 0.3, 0), (8.6, 104.9, 0.3, 0),
              (9.6, 98, 28, 0), (10, 97, 29.5, 0)],
        arcs=[(3.0, 4.2, 3.0), (8.6, 9.6, 3.5)])
    cam = Cam((90, -22, 14), (100, 20, 0), 1500)
    dt = 0.04
    ts = np.arange(0, 4.84, dt)

    def dist(team, t):
        b = ball_at(sc, t)
        return min(np.hypot(*(p - b[:2])) for _, tm, p in players_at(sc, t) if tm in team)

    def overlay(ax, cam, t, k, boxes, bp):
        u, v, r = bp
        if k == 0:
            call(ax, "red crosses", (u, v), (u + 60, v - 170), fc=LAB["A"])
        if k == 1:
            p = at(sc["players"]["H"]["h1"], t)
            ground_ring(ax, cam, p[0], p[1], 1.5, "#facc15", lw=1.3, fill="#facc15")
            call(ax, "blue defender ≤ 1.5 m, closer than any red", (u, v), (u - 120, v - 200), fc="#facc15",
                 color=INK)
        if k == 2:
            line3(ax, cam, [[105, 13.84, 0], [105, 30.34, 0]], color="#facc15", lw=2.2, zorder=3.6)
            call(ax, "ball over the goal line", (u, v), (u - 200, v - 180), fc="#facc15", color=INK)
        if k == 3:
            call(ax, "corner, taker team red (Smart Tagging)", (u, v), (u - 260, v - 200), fc=LAB["A"])

    def c1(ax):
        curve_axes(ax, T, "Distance from the ball to the nearest blue / red player (m), last 5 s before the ball goes out",
                   (0, 8), [0, 1.5, 4, 8])
        ax.plot(ts, [min(dist("HG", t), 8) for t in ts], color=LAB["H"], lw=1.1)
        ax.plot(ts, [min(dist("A", t), 8) for t in ts], color=LAB["A"], lw=1.1)
        ax.axhline(1.5, color="#d97706", lw=0.7, ls="--")
        ax.axvspan(4.84 - 5, 4.84, color="#fde68a", alpha=0.25, lw=0)

    return dict(T=T, scene=sc, cam=cam, overlay=overlay,
                frames=[(3.0, "cross"), (4.2, "last touch: header"), (4.84, "ball out"), (8.6, "corner kick")],
                strip=[("curve", c1),
                       ("ribbon", "Decoder output", [(0, 4.84, "A"), (4.84, 8.6, "D"), (8.6, T, "A")]),
                       ("ribbon", "After the ball-out rule (opponents' possession inserted)",
                        [(0, 4.2, "A"), (4.2, 4.84, "H"), (4.84, 8.6, "D"), (8.6, T, "A")])])


FIGS = [("fig1_ball_fusion.png", fig_ball), ("fig2_dead_ball_detector.png", fig_dead),
        ("fig3_possession_model.png", fig_model), ("fig4_touch_evidence.png", fig_touch),
        ("fig5_viterbi_decoder.png", fig_viterbi), ("fig6_whistle_rule.png", fig_whistle),
        ("fig7_ball_out_rule.png", fig_ballout)]

if __name__ == "__main__":
    out_dir = sys.argv[1]
    only = {int(a) for a in sys.argv[2:]}
    os.makedirs(out_dir, exist_ok=True)
    for i, (name, fn) in enumerate(FIGS, 1):
        if only and i not in only:
            continue
        build(fn(), os.path.join(out_dir, name))
        print("wrote", name)
