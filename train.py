"""Train + evaluate the CNN->BiLSTM baseline.

  python train.py --data synthetic                                  # pipeline smoke test, no download
  python train.py --data icentia --root /path/to/icentia11k --max-patients 200 --max-segments 5
  python train.py --data icentia --root ... --mode detected         # use our own R-peak detector
"""
import argparse, json
from dataclasses import replace
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

from afib.config import CFG
from afib.model import build_classifier
from afib.metrics import report, best_f1_threshold


def patient_split(groups, seed, frac=(0.7, 0.15, 0.15)):
    """Split by PATIENT so no patient appears in two sets (otherwise results are inflated)."""
    ids = np.unique(groups)
    np.random.default_rng(seed).shuffle(ids)
    a, b = int(frac[0] * len(ids)), int((frac[0] + frac[1]) * len(ids))
    sets = (ids[:a], ids[a:b], ids[b:])
    return [np.where(np.isin(groups, s))[0] for s in sets]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", choices=["synthetic", "icentia"], default="synthetic")
    ap.add_argument("--root"); ap.add_argument("--mode", choices=["annotated", "detected"], default="annotated")
    ap.add_argument("--max-patients", type=int); ap.add_argument("--max-segments", type=int)
    ap.add_argument("--epochs", type=int, default=CFG.epochs)
    ap.add_argument("--synthetic-patients", type=int, default=60)
    ap.add_argument("--out", default="results")
    ap.add_argument("--window-beats", type=int, default=CFG.window_beats)
    ap.add_argument("--stride-beats", type=int, default=CFG.stride_beats)
    a = ap.parse_args()
    cfg = replace(CFG, window_beats=a.window_beats, stride_beats=a.stride_beats)

    tf.keras.utils.set_random_seed(cfg.seed)
    out = Path(a.out); out.mkdir(exist_ok=True)

    if a.data == "synthetic":
        from afib.synthetic import synth_dataset
        X, y, g = synth_dataset(cfg, n_patients=a.synthetic_patients)
    else:
        from afib.icentia11k import build_dataset
        X, y, g = build_dataset(a.root, cfg, a.mode, a.max_patients, a.max_segments)
    print(f"windows={len(y)}  patients={len(np.unique(g))}  AFib fraction={y.mean():.3f}  X={X.shape}")

    tr, va, te = patient_split(g, cfg.seed)
    cw = dict(enumerate(compute_class_weight("balanced", classes=np.array([0, 1]), y=y[tr])))
    print("train/val/test windows:", len(tr), len(va), len(te), " class weights:", cw)

    model = build_classifier(cfg)
    model.summary()
    model.compile(tf.keras.optimizers.Adam(cfg.lr), "binary_crossentropy",
                  metrics=[tf.keras.metrics.AUC(name="auc"), tf.keras.metrics.AUC(curve="PR", name="pr_auc")])
    hist = model.fit(X[tr], y[tr], validation_data=(X[va], y[va]), epochs=a.epochs, batch_size=cfg.batch_size,
                     class_weight=cw, verbose=2, callbacks=[
        tf.keras.callbacks.EarlyStopping("val_pr_auc", mode="max", patience=6, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau("val_loss", factor=0.5, patience=3)])

    thr = best_f1_threshold(y[va], model.predict(X[va], verbose=0))
    res = {"val_threshold": thr,
           "test@0.5": report(y[te], model.predict(X[te], verbose=0), 0.5),
           "test@val_threshold": report(y[te], model.predict(X[te], verbose=0), thr),
           "n_test_windows": int(len(te)), "n_test_patients": int(len(np.unique(g[te])))}
    (out / "metrics.json").write_text(json.dumps(res, indent=2))
    model.save(out / "cnn_bilstm_baseline.keras")
    model.get_layer("bilstm")        # sanity: the layer attention will attach to exists
    print(json.dumps(res["test@val_threshold"], indent=2))

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.5))
    ax[0].plot(hist.history["loss"], label="train"); ax[0].plot(hist.history["val_loss"], label="val")
    ax[0].set_title("Loss"); ax[0].legend(); ax[0].set_xlabel("epoch")
    ax[1].plot(hist.history["pr_auc"], label="train"); ax[1].plot(hist.history["val_pr_auc"], label="val")
    ax[1].set_title("PR-AUC (AFib)"); ax[1].legend(); ax[1].set_xlabel("epoch")
    plt.tight_layout(); plt.savefig(out / "training_curves.png", dpi=130)

    r = res["test@val_threshold"]
    cm = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
    fig, ax = plt.subplots(figsize=(3.8, 3.4)); ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center", color="black")
    ax.set_xticks([0, 1], ["Non-AFib", "AFib"]); ax.set_yticks([0, 1], ["Non-AFib", "AFib"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title("Test confusion matrix")
    plt.tight_layout(); plt.savefig(out / "confusion_matrix.png", dpi=130)


if __name__ == "__main__":
    main()
