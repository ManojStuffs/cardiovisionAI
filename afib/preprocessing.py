"""Raw ECG -> clean ECG -> R-peaks.   (Tech stack slide: Signal Processing + R-peak Detection)"""
from __future__ import annotations
from fractions import Fraction

import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d

try:
    from scipy import signal
    _HAS_SCIPY_SIGNAL = True
except (ImportError, OSError):
    _HAS_SCIPY_SIGNAL = False


def _simple_find_peaks(x: np.ndarray, height: float | np.ndarray, distance: int):
    """Pure NumPy peak detector fallback when scipy.signal is restricted."""
    peaks = []
    n = len(x)
    is_arr = isinstance(height, np.ndarray)
    for i in range(1, n - 1):
        if x[i] > x[i - 1] and x[i] >= x[i + 1]:
            h = height[i] if is_arr else height
            if x[i] >= h:
                if not peaks or (i - peaks[-1]) >= distance:
                    peaks.append(i)
                elif x[i] > x[peaks[-1]]:
                    peaks[-1] = i
    return np.array(peaks, dtype=int), {}


def bandpass(ecg: np.ndarray, fs: float, low: float, high: float, order: int = 3) -> np.ndarray:
    """Zero-phase band-pass (zero phase so R-peaks are not shifted in time)."""
    if _HAS_SCIPY_SIGNAL:
        try:
            sos = signal.butter(order, [low, high], btype="bandpass", fs=fs, output="sos")
            return signal.sosfiltfilt(sos, ecg)
        except Exception:
            pass
    # Pure numpy/ndimage fallback: baseline removal + moving average smoothing
    baseline_win = max(3, int(fs / max(0.1, low)))
    smooth_win = max(1, int(fs / max(1.0, high)))
    baseline = uniform_filter1d(ecg, size=baseline_win)
    hp = ecg - baseline
    return uniform_filter1d(hp, size=smooth_win)


def resample(ecg: np.ndarray, fs_in: float, fs_out: float) -> np.ndarray:
    """Resample to target rate using polyphase or linear interpolation."""
    if int(fs_in) == int(fs_out):
        return ecg
    if _HAS_SCIPY_SIGNAL:
        try:
            frac = Fraction(int(fs_out), int(fs_in)).limit_denominator(1000)
            return signal.resample_poly(ecg, frac.numerator, frac.denominator)
        except Exception:
            pass
    num_out = int(round(len(ecg) * fs_out / fs_in))
    return np.interp(np.linspace(0, len(ecg) - 1, num_out), np.arange(len(ecg)), ecg)


def detect_r_peaks(ecg: np.ndarray, fs: float) -> np.ndarray:
    """Pan-Tompkins-style detector. Returns R-peak sample indices.

    band-pass 5-15 Hz -> derivative -> square -> moving-window integration ->
    adaptive threshold (30% of the local max over 8 s) -> refine to the true ECG maximum.
    ``ecg`` should already be band-passed (0.5-40 Hz).
    """
    qrs = bandpass(ecg, fs, 5.0, 15.0, order=2)
    mwi = uniform_filter1d(np.gradient(qrs) ** 2, size=max(1, int(0.15 * fs)))
    local_max = maximum_filter1d(mwi, size=int(8 * fs))
    local_max = uniform_filter1d(local_max, size=int(4 * fs))

    if _HAS_SCIPY_SIGNAL:
        try:
            cand, _ = signal.find_peaks(mwi, height=0.3 * local_max, distance=int(0.2 * fs))
        except Exception:
            cand, _ = _simple_find_peaks(mwi, height=0.3 * local_max, distance=int(0.2 * fs))
    else:
        cand, _ = _simple_find_peaks(mwi, height=0.3 * local_max, distance=int(0.2 * fs))

    half = int(0.08 * fs)                      # refine on the ECG itself; abs() handles inverted leads
    refined = []
    for c in cand:
        lo, hi = max(0, c - half), min(len(ecg), c + half + 1)
        refined.append(lo + int(np.argmax(np.abs(ecg[lo:hi]))))
    peaks = np.unique(refined)

    keep = []                                   # enforce physiological refractory period (0.2 s)
    for p in peaks:
        if keep and p - keep[-1] < int(0.2 * fs):
            if abs(ecg[p]) > abs(ecg[keep[-1]]):
                keep[-1] = p
        else:
            keep.append(p)
    return np.asarray(keep, dtype=int)


def match_peaks(pred: np.ndarray, ref: np.ndarray, fs: float, tol_s: float = 0.05):
    """Detector quality vs. reference beats: returns (sensitivity, PPV). Tolerance is +-50 ms."""
    tol = int(tol_s * fs)
    ref_used = np.zeros(len(ref), bool)
    tp = 0
    for p in pred:
        j = np.searchsorted(ref, p)
        best = None
        for k in (j - 1, j):
            if 0 <= k < len(ref) and not ref_used[k] and abs(ref[k] - p) <= tol:
                if best is None or abs(ref[k] - p) < abs(ref[best] - p):
                    best = k
        if best is not None:
            ref_used[best] = True
            tp += 1
    return tp / max(len(ref), 1), tp / max(len(pred), 1)


def preprocess_ecg(ecg: np.ndarray, fs_in: float, cfg) -> tuple[np.ndarray, int]:
    """Full signal stage: resample -> band-pass.  Returns (clean_ecg, fs_target)."""
    x = resample(np.asarray(ecg, dtype=np.float64), fs_in, cfg.fs_target)
    x = bandpass(x, cfg.fs_target, cfg.band_low, cfg.band_high)
    return x, cfg.fs_target
