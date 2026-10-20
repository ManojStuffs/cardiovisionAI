"""CNN (feature extraction) -> BiLSTM (sequence modelling).   Attention + final output come next.

Design for the next stage
-------------------------
* ``build_encoder`` stops at the BiLSTM and returns the FULL sequence (batch, 30, 2*units):
  one vector per beat. The Attention layer will consume exactly this tensor.
* CNN uses padding='same', so time steps stay 1:1 with beats. That is what lets attention weights
  later say "beat t drove the prediction".
* ``build_classifier`` adds a temporary pooling head so the encoder can be trained and evaluated NOW.
  When you add attention, swap that head for  Attention -> Dense(sigmoid).
"""
from __future__ import annotations
import tensorflow as tf
from tensorflow.keras import layers, Model


def build_encoder(cfg) -> Model:
    inp = layers.Input((cfg.window_beats, cfg.n_features), name="rr_sequence")
    x = inp
    for i, (f, k) in enumerate(zip(cfg.cnn_filters, cfg.cnn_kernels), 1):
        x = layers.Conv1D(f, k, padding="same", name=f"conv{i}")(x)
        x = layers.BatchNormalization(name=f"bn{i}")(x)
        x = layers.Activation("relu", name=f"relu{i}")(x)
    x = layers.SpatialDropout1D(cfg.dropout * 0.5, name="cnn_dropout")(x)
    seq = layers.Bidirectional(layers.LSTM(cfg.lstm_units, return_sequences=True, dropout=0.1),
                               name="bilstm")(x)                      # (batch, 30, 2*units)
    return Model(inp, seq, name="cnn_bilstm_encoder")


def build_classifier(cfg) -> Model:
    enc = build_encoder(cfg)
    seq = enc.output
    pooled = layers.Concatenate(name="pool")([layers.GlobalAveragePooling1D()(seq),
                                              layers.GlobalMaxPooling1D()(seq)])
    x = layers.Dense(32, activation="relu", name="head_dense")(pooled)
    x = layers.Dropout(cfg.dropout, name="head_dropout")(x)
    out = layers.Dense(1, activation="sigmoid", name="afib_prob")(x)
    return Model(enc.input, out, name="cnn_bilstm_baseline")
