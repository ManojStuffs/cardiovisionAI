"""Make fake ECG-paper pictures (pink grid, black trace) so you can test with NO data.

  python make_demo_images.py          ->  demo_images/normal_*.png, demo_images/afib_*.png
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from afib.synthetic import synth_ecg


def make_beats(kind, rng, seconds=12):
    if kind == "normal":
        base = rng.uniform(0.7, 1.0)
        rr = base + 0.02 * rng.standard_normal(40)
    else:                                              # AFib: irregularly irregular
        base = rng.uniform(0.55, 0.9)
        rr = base * rng.lognormal(0, 0.25, 40)
    rr = np.clip(rr, 0.35, 1.6)
    t = np.cumsum(rr); t = t[t < seconds]
    return t, np.full(len(t), 1 if kind == "afib" else 0)


def draw(kind, path, seed, seconds=10, fs=250):
    rng = np.random.default_rng(seed)
    t, lab = make_beats(kind, rng, seconds)
    ecg = synth_ecg(t, lab, fs, seconds, rng, noise=0.02)
    tt = np.arange(len(ecg)) / fs
    fig = plt.figure(figsize=(10, 2.6), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    for x in np.arange(0, seconds + 1e-9, 0.04):       # small grid  (1 mm = 0.04 s)
        ax.axvline(x, color="#ffd6d6", lw=0.5, zorder=0)
    for x in np.arange(0, seconds + 1e-9, 0.2):        # big grid    (5 mm = 0.2 s)
        ax.axvline(x, color="#ff9c9c", lw=0.9, zorder=0)
    for y in np.arange(-1, 1.6, 0.1):
        ax.axhline(y, color="#ffd6d6", lw=0.5, zorder=0)
    for y in np.arange(-1, 1.6, 0.5):
        ax.axhline(y, color="#ff9c9c", lw=0.9, zorder=0)
    ax.plot(tt, ecg, color="black", lw=1.1, zorder=3)
    ax.text(0.1, 1.25, "II", fontsize=9)               # a lead label, to check text is ignored
    ax.set_xlim(0, seconds); ax.set_ylim(-0.8, 1.5); ax.axis("off")
    fig.savefig(path); plt.close(fig)


if __name__ == "__main__":
    out = Path("demo_images"); out.mkdir(exist_ok=True)
    for i in range(3):
        draw("normal", out / f"normal_{i}.png", seed=100 + i)
        draw("afib", out / f"afib_{i}.png", seed=200 + i)
    print("wrote", sorted(p.name for p in out.glob("*.png")))
