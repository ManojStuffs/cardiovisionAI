"""Run:  python -m tests.test_pipeline     (no dataset needed)"""
import tempfile, os
import numpy as np
from afib.config import CFG
from afib.preprocessing import preprocess_ecg, detect_r_peaks, match_peaks, resample
from afib.rr_features import windows_from_beats
from afib.synthetic import synth_beats, synth_ecg
from afib.icentia11k import rhythm_at, beats_annotated, list_records, build_dataset


def test_resample_length():
    x = np.random.randn(128 * 10)
    assert abs(len(resample(x, 128, 250)) - 2500) <= 1
    assert resample(x, 250, 250) is x


def test_r_peak_detector_across_sampling_rates():
    rng = np.random.default_rng(1)
    t, lab = synth_beats(rng, 400)
    for fs in (128, 250, 360):
        ecg = synth_ecg(t, lab, fs, 120, rng)
        x, fs_t = preprocess_ecg(ecg, fs, CFG)
        peaks = detect_r_peaks(x, fs_t)
        ref = (t[t < 119] * fs_t).astype(int)
        se, ppv = match_peaks(peaks[peaks < 119 * fs_t], ref, fs_t)
        print(f"  fs={fs}: detector sensitivity={se:.3f} PPV={ppv:.3f}")
        assert se > 0.97 and ppv > 0.97


def test_windows_shape_and_labels():
    t = np.cumsum(np.full(201, 0.8)); lab = np.r_[np.zeros(100), np.ones(101)].astype(np.int8)
    X, y = windows_from_beats(t, lab, CFG)
    assert X.shape[1:] == (30, 3) and len(X) == len(y) and y[0] == 0 and y[-1] == 1
    lab[50] = -1                                           # unknown label -> windows containing it dropped
    X2, _ = windows_from_beats(t, lab, CFG)
    assert len(X2) < len(X)
    t[60:] += 5                                            # 5 s gap -> windows containing it dropped
    X3, _ = windows_from_beats(t, np.zeros(201, np.int8), CFG)
    assert len(X3) < len(windows_from_beats(np.cumsum(np.full(201, .8)), np.zeros(201, np.int8), CFG)[0])


def test_model_shapes():
    from afib.model import build_encoder, build_classifier
    enc, clf = build_encoder(CFG), build_classifier(CFG)
    x = np.random.randn(4, 30, 3).astype("float32")
    assert enc.predict(x, verbose=0).shape == (4, 30, 2 * CFG.lstm_units)   # one vector per beat -> attention-ready
    assert clf.predict(x, verbose=0).shape == (4, 1)


def test_icentia_loader_on_fake_record():
    import wfdb
    d = tempfile.mkdtemp(); sub = os.path.join(d, "p00", "p00007"); os.makedirs(sub)
    beats = (np.arange(1, 400) * 200).astype(int)                     # 0.8 s at 250 Hz
    samples = np.r_[[0, 200 * 200], beats]
    symbols = ["+", "+"] + ["N"] * len(beats)
    aux = ["(N", "(AFIB"] + [""] * len(beats)
    o = np.argsort(samples, kind="stable")
    wfdb.wrann("p00007_s00", "atr", samples[o], np.array(symbols)[o], aux_note=np.array(aux)[o], fs=250, write_dir=sub)
    recs = list_records(d); assert len(recs) == 1
    t, lab = beats_annotated(recs[0])
    assert np.allclose(np.diff(t), 0.8) and lab[0] == 0 and lab[-1] == 1 and (lab == 1).sum() > 100
    X, y, g = build_dataset(d, CFG)
    assert set(np.unique(y)) == {0, 1} and set(g) == {7}
    r = rhythm_at(np.array([5, 50]), np.array([10]), np.array([1], np.int8)); assert list(r) == [-1, 1]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            print(name); fn()
    print("ALL TESTS PASSED")
