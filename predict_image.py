"""ECG IMAGE in  ->  AFib verdict out.

  python predict_image.py my_ecg.png                    # trace spans 10 s (default)
  python predict_image.py my_ecg.png --seconds 6
  python predict_image.py my_ecg.png --out result.png   # also saves an annotated picture

Pipeline:  image -> digitise trace -> resample/band-pass -> R-peaks -> RR windows -> CNN+BiLSTM -> probability
"""
import argparse, json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from afib.config import CFG
from afib.image_to_ecg import digitize
from afib.preprocessing import preprocess_ecg, detect_r_peaks
from afib.rr_features import rr_features

DEFAULT_MODEL = Path(__file__).parent / "results_image_model" / "cnn_bilstm_baseline.keras"


def analyse(image_path, seconds=10.0, px_per_sec=None, model_path=DEFAULT_MODEL, model=None):
    import tensorflow as tf
    model = model or tf.keras.models.load_model(model_path)
    W = model.input_shape[1]
    thr_file = Path(model_path).parent / "metrics.json"
    thr = json.loads(thr_file.read_text())["val_threshold"] if thr_file.exists() else 0.5

    sig, fs, info = digitize(image_path, seconds, px_per_sec)
    x, fs_t = preprocess_ecg(sig, fs, CFG)
    peaks = detect_r_peaks(x, fs_t)
    t = peaks / fs_t
    rr = np.diff(t)
    res = dict(seconds=round(info["seconds"], 1), px_per_sec=round(fs, 1), n_beats=int(len(peaks)),
               heart_rate_bpm=round(60 / np.median(rr), 0) if len(rr) else None,
               rr_cv=round(float(np.std(rr) / np.mean(rr)), 3) if len(rr) > 1 else None,
               warnings=[])
    if fs < 60:
        res["warnings"].append(f"Low resolution ({fs:.0f} px/s): R-peak timing will be coarse. Use a larger image.")
    if len(rr) and not (35 <= res["heart_rate_bpm"] <= 200):
        res["warnings"].append("Heart rate looks implausible - check --seconds or whether the image is a single lead.")

    prob = np.array([])
    if len(rr) >= W:
        S = 1
        idx = np.arange(0, len(rr) - W + 1, S)[:, None] + np.arange(W)[None, :]
        rr_w = np.clip(rr[idx], CFG.rr_min, CFG.rr_max)
        prob = model.predict(rr_features(rr_w), verbose=0).ravel()
        flagged = float((prob >= thr).mean())
        res.update(afib_probability=round(float(np.mean(prob)), 3), windows=int(len(prob)),
                   windows_flagged=round(flagged, 2),
                   verdict="AFib LIKELY" if flagged >= 0.5 else "No AFib detected")
    else:
        res.update(verdict="INCONCLUSIVE", afib_probability=None,
                   reason=f"Only {len(peaks)} beats found; need at least {W + 1}. Use a longer strip.")
    return res, dict(sig=sig, fs=fs, t_peaks=t, info=info, prob=prob, x=x, fs_t=fs_t, peaks=peaks)


def save_figure(res, d, out):
    fig, ax = plt.subplots(2, 1, figsize=(11, 6), gridspec_kw=dict(height_ratios=[1, 1.4]))
    ax[0].imshow(d["info"]["image"][:, :, ::-1]); ax[0].axis("off"); ax[0].set_title("Input image")
    tt = np.arange(len(d["x"])) / d["fs_t"]
    ax[1].plot(tt, d["x"], lw=0.8, color="k")
    ax[1].plot(d["peaks"] / d["fs_t"], d["x"][d["peaks"]], "rv", label=f"R-peaks ({res['n_beats']})")
    ax[1].set_xlabel("seconds"); ax[1].set_yticks([]); ax[1].legend(loc="upper right")
    col = "crimson" if res["verdict"].startswith("AFib") else ("gray" if res["verdict"] == "INCONCLUSIVE" else "seagreen")
    p = res["afib_probability"]
    ax[1].set_title(f"{res['verdict']}   (AFib probability = {p if p is not None else 'n/a'},  "
                    f"HR ~ {res['heart_rate_bpm']} bpm)", color=col, fontweight="bold")
    plt.tight_layout(); plt.savefig(out, dpi=120); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--seconds", type=float, default=10.0, help="how many seconds the trace spans (default 10)")
    ap.add_argument("--px-per-sec", type=float, help="alternative to --seconds")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--out", help="save annotated result picture here")
    a = ap.parse_args()
    res, d = analyse(a.image, a.seconds, a.px_per_sec, a.model)
    print(json.dumps(res, indent=2))
    if a.out:
        save_figure(res, d, a.out)
        print("saved", a.out)


if __name__ == "__main__":
    main()
