"""Icentia11k (PhysioNet) loader.

Layout:  <root>/p00/p00000/p00000_s00.{dat,hea,atr}     250 Hz, single-lead, ~70 min per segment
Beat annotations: N (normal) S (PAC) V (PVC) Q (unclassified)
Rhythm annotations: symbol '+' with aux_note '(N' | '(AFIB' | '(AFL'
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np

from .config import BEAT_SYMBOLS, RHYTHM_LABEL
from .preprocessing import preprocess_ecg, detect_r_peaks
from .rr_features import windows_from_beats


def list_records(root: str | Path) -> list[Path]:
    """All record stems (no extension), sorted."""
    return sorted(p.with_suffix("") for p in Path(root).rglob("p?????_s??.atr"))


def patient_id(record: Path) -> int:
    return int(re.search(r"p(\d{5})_s\d{2}", record.name).group(1))


def _read_annotations(record: Path):
    import wfdb
    ann = wfdb.rdann(str(record), "atr")
    sample, symbol, aux = np.asarray(ann.sample), np.asarray(ann.symbol), ann.aux_note
    beat_mask = np.isin(symbol, list(BEAT_SYMBOLS))
    rhythm_idx = [i for i, s in enumerate(symbol) if s == "+" and aux[i].strip("\x00") in RHYTHM_LABEL]
    r_samples = sample[rhythm_idx]
    r_labels = np.array([RHYTHM_LABEL[aux[i].strip("\x00")] for i in rhythm_idx], dtype=np.int8)
    return sample[beat_mask], r_samples, r_labels


def rhythm_at(beat_samples: np.ndarray, r_samples: np.ndarray, r_labels: np.ndarray) -> np.ndarray:
    """Rhythm label in force at each beat (-1 before the first rhythm annotation)."""
    if len(r_samples) == 0:
        return np.full(len(beat_samples), -1, np.int8)
    k = np.searchsorted(r_samples, beat_samples, side="right") - 1
    out = r_labels[np.clip(k, 0, None)].copy()
    out[k < 0] = -1
    return out


def beats_annotated(record: Path, fs: int = 250):
    """Fast path: use the dataset's own beat labels (only reads .atr, no signal)."""
    beats, r_s, r_l = _read_annotations(record)
    return beats / fs, rhythm_at(beats, r_s, r_l)


def beats_detected(record: Path, cfg):
    """Full path: raw ECG -> resample -> band-pass -> R-peak detection. Mirrors deployment."""
    import wfdb
    rec = wfdb.rdrecord(str(record))
    ecg, fs = preprocess_ecg(rec.p_signal[:, 0], rec.fs, cfg)
    peaks = detect_r_peaks(ecg, fs)
    _, r_s, r_l = _read_annotations(record)
    r_s = r_s * (fs / rec.fs)                              # annotation samples -> resampled axis
    return peaks / fs, rhythm_at(peaks, r_s, r_l)


def build_dataset(root, cfg, mode="annotated", max_patients=None, max_segments=None):
    """Returns X, y, groups (patient id per window)."""
    recs = list_records(root)
    if not recs:
        raise FileNotFoundError(f"No Icentia11k records (pXXXXX_sYY.atr) under {root}")
    pats = set(sorted({patient_id(r) for r in recs})[:max_patients])
    Xs, ys, gs, seg_count = [], [], [], {}
    for r in recs:
        pid = patient_id(r)
        if pid not in pats:
            continue
        if max_segments and seg_count.get(pid, 0) >= max_segments:
            continue
        seg_count[pid] = seg_count.get(pid, 0) + 1
        t, lab = beats_annotated(r) if mode == "annotated" else beats_detected(r, cfg)
        X, y = windows_from_beats(t, lab, cfg)
        if len(y):
            Xs.append(X); ys.append(y); gs.append(np.full(len(y), pid))
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(gs)
