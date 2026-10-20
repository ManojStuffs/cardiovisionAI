"""Beat times -> RR-interval windows (model input).  (Tech stack slide: RR-Interval Sequencing)

Common currency of the whole project: ``beat_times`` (seconds) + ``beat_labels``
(1 = AFib, 0 = non-AFib, -1 = unknown/excluded). Real data and synthetic data both end up here.
"""
from __future__ import annotations
import numpy as np


def windows_from_beats(beat_times: np.ndarray, beat_labels: np.ndarray, cfg):
    """Slide a window of ``cfg.window_beats`` RR intervals over a record.

    Returns X (n, window, n_features) float32, y (n,) int8.
    Windows are dropped if they contain an implausible RR (< rr_min or > rr_max) or any unknown label.
    """
    rr = np.diff(beat_times)
    lab = np.asarray(beat_labels)[1:]                      # label of the beat that ends each interval
    W, S = cfg.window_beats, cfg.stride_beats
    if len(rr) < W:
        return np.empty((0, W, cfg.n_features), np.float32), np.empty((0,), np.int8)

    starts = np.arange(0, len(rr) - W + 1, S)
    idx = starts[:, None] + np.arange(W)[None, :]
    rr_w, lab_w = rr[idx], lab[idx]

    ok = (rr_w.min(1) >= cfg.rr_min) & (rr_w.max(1) <= cfg.rr_max) & (lab_w.min(1) >= 0)
    rr_w, lab_w = rr_w[ok], lab_w[ok]
    y = (lab_w.mean(1) >= cfg.afib_fraction).astype(np.int8)
    return rr_features(rr_w), y


def rr_features(rr_w: np.ndarray) -> np.ndarray:
    """(n, W) RR seconds -> (n, W, 3) channels.

    ch0  RR in seconds                  (absolute rate)
    ch1  dRR = RR[t] - RR[t-1]          (beat-to-beat irregularity, the key AFib cue)
    ch2  RR / median(RR in window)      (rate-independent irregularity)
    """
    rr_w = rr_w.astype(np.float32)
    d = np.diff(rr_w, axis=1, prepend=rr_w[:, :1])
    rel = rr_w / np.median(rr_w, axis=1, keepdims=True)
    return np.stack([rr_w, d, rel], axis=-1).astype(np.float32)
