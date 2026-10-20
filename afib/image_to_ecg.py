"""ECG picture -> 1-D signal.

Works on a picture of ONE lead / rhythm strip (crop a 12-lead printout to a single row first).
Idea: the trace is the dark line, the grid is coloured/light. Keep dark pixels, drop small blobs
(text, labels), then for every pixel column read where the trace is.

Time axis: you tell us how many seconds the trace spans (standard strips = 10 s)
or give px_per_sec directly. Voltage axis is arbitrary units (the model only uses R-peak timing).
"""
from __future__ import annotations
import cv2
import numpy as np


def trace_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Boolean mask of trace pixels (dark on a lighter / coloured grid)."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    darkest_channel = img_bgr.max(axis=2)            # pink / red / green grids have one bright channel
    v = np.minimum(gray, darkest_channel)
    thr, _ = cv2.threshold(v.astype(np.uint8), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thr = min(thr, 140)                              # never let a mid-grey grid count as trace
    mask = (v <= thr).astype(np.uint8)

    # keep only wide components (the trace); text and lead labels are small
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    keep = np.zeros_like(mask)
    min_w = 0.25 * img_bgr.shape[1]
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_WIDTH] >= min_w:
            keep[lab == i] = 1
    if keep.sum() == 0:                              # trace broken into pieces: fall back to all dark pixels
        keep = mask
    return keep.astype(bool)


def digitize(path: str, seconds: float | None = 10.0, px_per_sec: float | None = None):
    """Returns (signal, fs, info).  signal is upward-positive, fs = samples (pixel columns) per second."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    mask = trace_mask(img)
    cols = np.where(mask.any(axis=0))[0]
    if len(cols) < 20:
        raise ValueError("No ECG trace found in the image (is the line dark on a light background?)")
    x0, x1 = cols[0], cols[-1]

    ys = np.full(x1 - x0 + 1, np.nan)
    base = np.median(np.where(mask)[0])               # baseline = typical trace height
    for k, x in enumerate(range(x0, x1 + 1)):
        col = np.where(mask[:, x])[0]
        if len(col):                                   # pick the pixel furthest from baseline -> sharp R peaks survive
            ys[k] = col[np.argmax(np.abs(col - base))] if len(col) > 3 else col.mean()
    good = ~np.isnan(ys)
    ys = np.interp(np.arange(len(ys)), np.flatnonzero(good), ys[good])
    sig = -(ys - np.median(ys))                       # image y grows downward -> flip

    if px_per_sec is None:
        px_per_sec = len(sig) / float(seconds)
    info = dict(width_px=int(len(sig)), px_per_sec=float(px_per_sec), seconds=len(sig) / px_per_sec,
                mask=mask, x0=int(x0), image=img)
    return sig, float(px_per_sec), info
