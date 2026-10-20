"""Raw ECG array -> AFib probability per window. Full deployment path through the BiLSTM model.

  from predict import predict_ecg
  t_centres, prob = predict_ecg(ecg, fs, "results/cnn_bilstm_baseline.keras")
"""
import numpy as np
from afib.config import CFG
from afib.preprocessing import preprocess_ecg, detect_r_peaks
from afib.rr_features import rr_features


def predict_ecg(ecg, fs, model_path, cfg=CFG):
    import tensorflow as tf
    model = tf.keras.models.load_model(model_path)
    x, fs_t = preprocess_ecg(ecg, fs, cfg)
    beats = detect_r_peaks(x, fs_t) / fs_t
    rr = np.diff(beats)
    W, S = cfg.window_beats, cfg.stride_beats
    if len(rr) < W:
        return np.array([]), np.array([])
    idx = np.arange(0, len(rr) - W + 1, S)[:, None] + np.arange(W)[None, :]
    rr_w = np.clip(rr[idx], cfg.rr_min, cfg.rr_max)
    prob = model.predict(rr_features(rr_w), verbose=0).ravel()
    return beats[idx[:, W // 2] + 1], prob
