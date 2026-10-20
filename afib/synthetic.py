"""Synthetic data for testing the pipeline WITHOUT Icentia11k. NOT a substitute for real results.

* synth_beats()  -> beat_times + labels for a paroxysmal-AF record (normal <-> AFib episodes)
* synth_ecg()    -> a raw ECG waveform for a given beat sequence (to test filter + R-peak detector)
"""
from __future__ import annotations
import numpy as np

from .rr_features import windows_from_beats


def synth_beats(rng: np.random.Generator, n_beats: int = 6000):
    """Alternating sinus / AFib episodes. Sinus has RSA + occasional PACs (so it is not trivially regular);
    AFib has independent, log-normally scattered RR intervals ('irregularly irregular')."""
    rr, lab = [], []
    afib = bool(rng.random() < 0.3)
    while len(rr) < n_beats:
        n = int(rng.integers(100, 800))
        base = rng.uniform(0.55, 1.1)
        if afib:
            seg = base * rng.lognormal(0.0, rng.uniform(0.12, 0.30), n)
        else:
            ar = np.zeros(n)
            for i in range(1, n):
                ar[i] = 0.8 * ar[i - 1] + rng.normal(0, rng.uniform(0.01, 0.03))
            seg = base + ar + 0.03 * np.sin(2 * np.pi * np.cumsum(np.full(n, base)) / rng.uniform(3.5, 5))
            for i in np.where(rng.random(n - 1) < 0.02)[0]:        # PAC: short RR then compensatory pause
                seg[i], seg[i + 1] = 0.65 * seg[i], 1.35 * seg[i + 1]
        rr.extend(np.clip(seg, 0.3, 1.8)); lab.extend([int(afib)] * n)
        afib = not afib
    rr, lab = np.array(rr[:n_beats]), np.array(lab[:n_beats], np.int8)
    return np.concatenate([[0.0], np.cumsum(rr)]), np.concatenate([[lab[0]], lab])


def synth_dataset(cfg, n_patients=60, beats_per_patient=6000, seed=0):
    rng = np.random.default_rng(seed)
    Xs, ys, gs = [], [], []
    for pid in range(n_patients):
        t, lab = synth_beats(rng, beats_per_patient)
        X, y = windows_from_beats(t, lab, cfg)
        Xs.append(X); ys.append(y); gs.append(np.full(len(y), pid))
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(gs)


def synth_ecg(beat_times, labels, fs, duration, rng, noise=0.03):
    """PQRST template at each beat + baseline wander + 50 Hz hum + noise. AFib: no P wave, f-waves instead."""
    t = np.arange(int(duration * fs)) / fs
    ecg = np.zeros_like(t)
    waves = [(-0.20, 0.12, 0.025, "P"), (-0.04, -0.10, 0.010, ""), (0.0, 1.0, 0.012, ""),
             (0.04, -0.20, 0.010, ""), (0.26, 0.30, 0.050, "")]
    for bt, lb in zip(beat_times, labels):
        if bt > duration:
            break
        for off, amp, w, tag in waves:
            if tag == "P" and lb == 1:
                continue
            c = bt + off
            lo, hi = max(0, int((c - 5 * w) * fs)), min(len(t), int((c + 5 * w) * fs))
            ecg[lo:hi] += amp * np.exp(-0.5 * ((t[lo:hi] - c) / w) ** 2)
    if np.any(labels == 1):
        ecg += 0.03 * np.sin(2 * np.pi * rng.uniform(4, 8) * t) * np.interp(t, beat_times, labels)
    ecg += 0.3 * np.sin(2 * np.pi * 0.3 * t) + 0.02 * np.sin(2 * np.pi * 50 * t) + rng.normal(0, noise, len(t))
    return ecg
