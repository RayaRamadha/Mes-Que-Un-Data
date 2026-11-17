"""Rule "last touch before the ball goes out" (notebook section 8d).

Laws of the Game: a corner kick or goal kick (and a throw-in) is awarded to the OPPONENTS of the team that touched the
ball last. If the prediction gives the possession to the restart taker (R) right up to the moment the ball goes out,
the other team's (¬R) last touch (a clearance, a goalkeeper save, a deflection) was missed as a possession. The rule
inserts a ¬R possession from the last ¬R touch (nearest ¬R player ≤ r m from the ball and closer than any R player,
searched back ≤ 5 s from the moment the ball goes out) until the ball goes out.

Restart types are returned with their Indonesian names, which the notebook uses as keys:
"sepak pojok" = corner kick, "tendangan gawang" = goal kick, "lemparan ke dalam" = throw-in, "lain" = other.
"""
import numpy as np

FPS = 25


def nearest_dist(P, home, ball):
    """distance from the ball to the nearest home / away player per frame (inf when there is none)"""
    d = np.linalg.norm(P - ball[:, None, :], axis=-1)
    d = np.where(np.isfinite(d), d, np.inf)
    return d[:, home].min(1), d[:, ~home].min(1)


def last_touch(d_other, d_r, o, r_m, back_s=5.0, fps=FPS):
    """last frame in [o − back_s, o) where the nearest ¬R player is ≤ r_m m from the ball and closer than any R player;
    None if there is no such frame"""
    a = max(0, int(o - back_s * fps))
    m = (d_other[a:o] <= r_m) & (d_other[a:o] < d_r[a:o])
    k = np.flatnonzero(m)
    return int(a + k[-1]) if len(k) else None


def idsse_restarts(d):
    """restarts after a dead ball in IDSSE: ball-out frame o (first dead frame), restart frame r, restart type "jenis"
    (from the ball position at the restart), taker R (flag after the restart), last toucher "terakhir" (flag before the
    ball goes out) and the start "awal_spell" of the last ¬R flag spell"""
    st, poss, ball, half = d["status"], d["poss"], d["ball"], d["half"]
    L, W, T = float(d["L"]), float(d["W"]), len(st)
    outs = np.flatnonzero((st[:-1] == 1) & (st[1:] == 0)) + 1
    rows = []
    for o in outs:
        rr = np.flatnonzero(st[o:] == 1)
        if not len(rr):
            continue
        r = int(o + rr[0])
        if r - o > 180 * FPS or half[o - 1] != half[min(r, T - 1)] or half[o - 1] == 0:
            continue
        bb = ball[r:r + 6]
        bb = bb[np.isfinite(bb).all(1)]
        if not len(bb):
            continue
        x, y = bb[0]
        if min(x, L - x) < 2.5 and min(y, W - y) < 2.5:
            typ = "sepak pojok"
        elif min(x, L - x) < 6.5 and abs(y - W / 2) < 10.5:
            typ = "tendangan gawang"
        elif min(y, W - y) < 2.0:
            typ = "lemparan ke dalam"
        else:
            typ = "lain"
        pr = poss[r + 2:r + 25]
        pr = pr[pr >= 0]
        if not len(pr) or poss[o - 1] < 0:
            continue
        R = int(np.bincount(pr, minlength=2).argmax())
        last = int(poss[o - 1])
        k = o - 1
        while k > 0 and poss[k - 1] == last:
            k -= 1
        rows.append({"o": int(o), "r": r, "jenis": typ, "R": R, "terakhir": last, "awal_spell": int(k)})
    return rows


def iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return inter / union if union > 0 else 0.0


def att_dir(d):
    """attacking direction of the home team per half (+1 = towards large x), from the mean player position at the start
    of the half"""
    att = np.zeros(len(d["status"]), np.int8)
    for h in (1, 2):
        m = np.flatnonzero((d["half"] == h) & (d["status"] == 1))[:250]
        hx = np.nanmean(d["P"][m][:, d["home"].astype(bool), 0])
        att[d["half"] == h] = 1 if hx < d["L"] / 2 else -1
    return att


def flag_labels(d):
    """IDSSE labels with touch semantics: H/A from the BallPossession flag, D from BallStatus; live frames without a flag
    take the last known flag"""
    st, po = d["status"], d["poss"]
    gt = np.where(st == 0, "D", np.where(po == 1, "H", np.where(po == 0, "A", "?"))).astype(object)
    unk = np.flatnonzero(gt == "?")
    if len(unk):
        known = np.where(np.isin(gt, ["H", "A"]), np.arange(len(gt)), -1)
        last = np.maximum.accumulate(known)
        nxt = np.minimum.accumulate(np.where(known >= 0, known, len(gt))[::-1])[::-1]
        src = np.where(last[unk] >= 0, last[unk], np.minimum(nxt[unk], len(gt) - 1))
        gt[unk] = gt[src]
        gt[unk[gt[unk] == "?"]] = "H"
    return gt


def decode3(lg, dead, prior, viterbi, cost=10.0):
    L = lg + prior
    emis = np.zeros((len(L), 3))
    emis[:, 0], emis[:, 1] = 0.5 * L, -0.5 * L
    emis[dead, :2] = -1e4
    emis[dead, 2] = 1e4
    emis[~dead, 2] = -1e4
    C = np.array([[0, cost, 0], [cost, 0, 0], [0, 0, 0]], float)
    return np.array(["H", "A", "D"], dtype=object)[viterbi(emis, C)]


def insert_last_touch(lab, o, R, d_other, d_r, r_m):
    """insertion variant: if the label right before o is team R, insert ¬R from the last ¬R touch until o"""
    tR, tN = ("H", "A") if R == 1 else ("A", "H")
    if o < 1 or lab[o - 1] != tR:
        return False
    tk = last_touch(d_other, d_r, o, r_m)
    if tk is None:
        return False
    a = tk
    while a < o and lab[a] != tR:
        a += 1
    seg = np.arange(a, o)
    seg = seg[lab[seg] == tR]
    lab[seg] = tN
    return len(seg) > 0
