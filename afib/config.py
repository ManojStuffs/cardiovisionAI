"""Central settings. Every number here is a design choice you can tune."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # ---- signal preprocessing -------------------------------------------------
    fs_target: int = 250          # every record is resampled to this rate (the "sampling-rate fix")
    band_low: float = 0.5         # Hz, removes baseline wander
    band_high: float = 40.0       # Hz, removes EMG / powerline
    # ---- RR sequencing --------------------------------------------------------
    window_beats: int = 30        # RR intervals per model input
    stride_beats: int = 10        # sliding-window hop
    rr_min: float = 0.20          # s; shorter than this is a detection artefact
    rr_max: float = 3.00          # s; longer than this is a gap / pause, window dropped
    n_features: int = 3           # [RR, dRR, RR/median(RR in window)]
    # ---- labels ---------------------------------------------------------------
    afib_fraction: float = 0.5    # window is AFib if >= this fraction of its beats are in AFib
    # ---- model (up to BiLSTM) -------------------------------------------------
    cnn_filters: tuple = (32, 64)
    cnn_kernels: tuple = (5, 3)
    lstm_units: int = 64
    dropout: float = 0.3
    # ---- training -------------------------------------------------------------
    batch_size: int = 128
    epochs: int = 30
    lr: float = 1e-3
    seed: int = 42


CFG = Config()

# Icentia11k annotation symbols
BEAT_SYMBOLS = {"N", "S", "V", "Q"}               # normal, PAC, PVC, unclassified
RHYTHM_LABEL = {"(N": 0, "(AFIB": 1, "(AFL": -1}   # AFL (flutter) is excluded, not treated as normal
