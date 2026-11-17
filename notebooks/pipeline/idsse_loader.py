"""IDSSE parser (DFL, Bundesliga, CC BY 4.0) → cache/external/id_<match>.npz.

npz content (25 fps, coordinates 0..L × 0..W metres):
  P (T, K, 2) players (no referees) · home (K,) · ball (T, 2) · poss (T,) 1 = home / 0 = away / −1 unknown
  (DFL BallPossession flag: changes at every touch) · status (T,) 1 alive / 0 dead (BallStatus) · half (T,) · L, W, fps
Used by the notebook (section 8d) to validate the rule "last touch before the ball goes out".
"""
from array import array
from pathlib import Path

import numpy as np
from lxml import etree


def _home_id(info_path):
    root = etree.parse(str(info_path)).getroot()
    for el in root.iter("Teams", "General"):
        if el.get("HomeTeamId"):
            return el.get("HomeTeamId")
    for el in root.iter("Team"):
        if el.get("Role") == "home":
            return el.get("TeamId")
    raise ValueError("HomeTeamId not found in " + str(info_path))


def parse_positions(pos_path, info_path):
    home_id = _home_id(info_path)
    people, ball = {}, {"N": array("i"), "X": array("f"), "Y": array("f"), "P": array("b"), "S": array("b"), "H": array("b")}
    cur, n_min, n_max = None, None, None
    L, W = 105.0, 68.0
    for ev, el in etree.iterparse(str(pos_path), events=("start", "end"), tag=("FrameSet", "Frame", "PitchSize")):
        if el.tag == "PitchSize" and ev == "end":
            L, W = float(el.get("X")), float(el.get("Y"))
        elif el.tag == "FrameSet" and ev == "start":
            team, pid = el.get("TeamId"), el.get("PersonId")
            half = 1 if el.get("GameSection") == "firstHalf" else 2
            if team == "BALL":
                cur = ("ball", None, half)
            elif team == "referee":
                cur = None
            else:
                key = (pid, team == home_id)
                people.setdefault(key, {"N": array("i"), "X": array("f"), "Y": array("f")})
                cur = ("p", key, half)
        elif el.tag == "Frame" and ev == "end":
            if cur is not None:
                n = int(el.get("N"))
                x, y = float(el.get("X")), float(el.get("Y"))
                if cur[0] == "ball":
                    ball["N"].append(n), ball["X"].append(x), ball["Y"].append(y)
                    bp = el.get("BallPossession")
                    ball["P"].append(1 if bp == "1" else (0 if bp == "2" else -1))
                    ball["S"].append(1 if el.get("BallStatus") == "1" else 0)
                    ball["H"].append(cur[2])
                    n_min = n if n_min is None else min(n_min, n)
                    n_max = n if n_max is None else max(n_max, n)
                else:
                    d = people[cur[1]]
                    d["N"].append(n), d["X"].append(x), d["Y"].append(y)
            el.clear()
        elif el.tag == "FrameSet" and ev == "end":
            cur = None
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    T = n_max - n_min + 1
    bN = np.frombuffer(ball["N"], np.int32) - n_min
    out_ball = np.full((T, 2), np.nan, np.float32)
    out_ball[bN, 0] = np.frombuffer(ball["X"], np.float32) + L / 2
    out_ball[bN, 1] = np.frombuffer(ball["Y"], np.float32) + W / 2
    poss = np.full(T, -1, np.int8)
    poss[bN] = np.frombuffer(ball["P"], np.int8)
    status = np.zeros(T, np.int8)
    status[bN] = np.frombuffer(ball["S"], np.int8)
    half = np.zeros(T, np.int8)
    half[bN] = np.frombuffer(ball["H"], np.int8)
    keys = sorted(people, key=lambda k: (not k[1], k[0]))
    P = np.full((T, len(keys), 2), np.nan, np.float32)
    for j, k in enumerate(keys):
        d = people[k]
        nn = np.frombuffer(d["N"], np.int32) - n_min
        ok = (nn >= 0) & (nn < T)
        P[nn[ok], j, 0] = np.frombuffer(d["X"], np.float32)[ok] + L / 2
        P[nn[ok], j, 1] = np.frombuffer(d["Y"], np.float32)[ok] + W / 2
    home = np.array([k[1] for k in keys])
    return dict(P=P, home=home, ball=out_ball, poss=poss, status=status, half=half, L=L, W=W, fps=25, n0=n_min)


def load_idsse(ext_dir, cache_dir):
    """all IDSSE matches; cached per match (the first parse takes ± 1–2 minutes per match)"""
    ext_dir, cache_dir = Path(ext_dir), Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for pos in sorted(ext_dir.glob("DFL_04_03_positions_raw_observed_*.xml")):
        mid = pos.stem.split("_")[-1]
        cp = cache_dir / "id_{}.npz".format(mid)
        if not cp.is_file():
            info = next(ext_dir.glob("DFL_02_01_matchinformation_*{}.xml".format(mid)))
            np.savez_compressed(cp, **parse_positions(pos, info))
        with np.load(cp) as zf:
            out[mid] = {k: zf[k] for k in zf.files}
    return out
