"""Install the trained weights shipped with the repository into cache/, so the notebook loads them instead of retraining.

    .venv\\Scripts\\python notebooks\\pipeline\\pasang_artefak.py

- artefak/yolo/best.pt (+ student_key.json): YOLO26s ball detector fine-tuned on auto-labelled tactical frames (section 2b).
  Without it, section 2b re-creates the labels and retrains (± 2 GPU hours, not bit-reproducible).
  artefak/yolo/results.csv is its training log (loss and validation metrics per epoch), read by the training report.
- artefak/kit/kit3_*: LightGBM kit-colour classifiers H / A / other (section 7b.1).
These are model weights, not match data: they cannot reconstruct tracking or video.
"""
import hashlib
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = ROOT / "cache"
COPIES = [
    (HERE / "artefak/yolo/best.pt", CACHE / "yolo/student/weights/best.pt"),
    (HERE / "artefak/yolo/student_key.json", CACHE / "yolo/student_key.json"),
    (HERE / "artefak/yolo/results.csv", CACHE / "yolo/student/results.csv"),
] + [(HERE / "artefak/kit" / "kit3_{}{}".format(s, x), CACHE / "touch" / "kit3_{}{}".format(s, x))
     for s in ("tactical", "broadcast") for x in (".txt", ".json", "_key.json")]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


for src, dst in COPIES:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print("{:<55} -> {}  (sha256 {}...)".format(str(src.relative_to(ROOT)), dst.relative_to(ROOT), sha(dst)))
print("done: {} files installed in {}".format(len(COPIES), CACHE))
