# AFib Detection — pipeline up to the BiLSTM stage

Mirrors the slides: **Icentia11k → signal processing → R-peaks → RR sequences → CNN → BiLSTM**.
Attention + final output are the next stage (the model is already shaped for it, see below).

## Layout
| File | Slide / stage |
|---|---|
| `afib/icentia11k.py` | Dataset loader (wfdb); beat + rhythm annotations → labels |
| `afib/preprocessing.py` | Resample to 250 Hz (sampling-rate fix), 0.5–40 Hz band-pass, Pan-Tompkins R-peak detector |
| `afib/rr_features.py` | RR intervals → 30-beat windows, 3 channels (RR, ΔRR, RR/median) |
| `afib/model.py` | **CNN (2 conv blocks) → BiLSTM(64)**; `build_encoder` returns per-beat sequence (30×128) |
| `train.py` | Patient-wise split, class weights, sensitivity/specificity/F1 on AFib class |
| `predict.py` | Raw ECG array → AFib probability per window |
| `afib/synthetic.py` | Synthetic ECG/RR generator, for testing only |
| `tests/test_pipeline.py` | `python -m tests.test_pipeline` |

## Run
```bash
pip install -r requirements.txt
python -m tests.test_pipeline                         # sanity check, no data needed
python train.py --data synthetic                      # smoke test of training code

# real data: download Icentia11k from PhysioNet first
python train.py --data icentia --root /path/to/icentia11k --max-patients 200 --max-segments 5
python train.py --data icentia --root /path/to/icentia11k --mode detected   # use our own R-peak detector
```
Outputs go to `results/`: `metrics.json`, `training_curves.png`, `confusion_matrix.png`, `cnn_bilstm_baseline.keras`.

## Adding Attention next
`build_encoder(cfg)` ends at the BiLSTM and outputs `(batch, 30, 128)` — one vector per beat
(conv layers use `padding="same"`, so time steps stay 1:1 with beats). In `model.py`, replace the pooling head in
`build_classifier` with: `Attention(seq) -> context vector -> Dense(1, sigmoid)`, and keep the attention weights as a
second model output for the dashboard's "which beats mattered" view.

## Design choices to know about
* **Labels:** window = AFib if ≥50% of its beats are in an `(AFIB` rhythm. Atrial flutter (`(AFL`) windows are **excluded**, not counted as normal.
* **Dropped windows:** any RR < 0.2 s or > 3 s, or any beat with unknown rhythm.
* **Split by patient**, never by window — otherwise results leak and look better than they are.
* **Threshold** is tuned on validation only; test metrics are reported at 0.5 and at that threshold.
* `--mode annotated` (default) uses Icentia11k's own beat labels and reads only `.atr` files (fast). `--mode detected`
  runs the full signal path, which is closer to deployment but slower.

## Verified so far (sandbox, no real data)
* All unit tests pass; R-peak detector: sensitivity ≥ 0.995, PPV = 1.0 on synthetic ECG at 128/250/360 Hz.
* Loader verified against a fake record written in the real Icentia11k annotation format.
* Training/eval run end-to-end on synthetic data (results in `results_synthetic_smoke_test/`).
  **Those scores (~99.7% F1) only prove the code runs — synthetic AFib is far easier than real AFib.**
  Real performance must come from running on Icentia11k.

## NEW: ECG image in -> AFib verdict out (no dataset needed)
```bash
pip install -r requirements.txt opencv-python-headless
python make_demo_images.py                                   # makes demo_images/normal_*.png, afib_*.png
python predict_image.py demo_images/afib_0.png --out result.png
python predict_image.py my_ecg.png --seconds 10 --out result.png   # your own picture
```
Image rules: ONE lead / rhythm strip (crop 12-lead printouts to one row), dark trace on a light or
coloured grid, >= ~8 s long, >= ~800 px wide. `--seconds` = how many seconds the trace spans (standard strip = 10).

Files: `afib/image_to_ecg.py` (picture -> signal), `predict_image.py` (verdict + annotated figure),
`results_image_model/` (8-beat-window model; a 10 s strip has only ~12 beats, so the 30-beat model cannot be used).
Retrain it: `python train.py --data synthetic --window-beats 8 --stride-beats 3 --jitter-ms 6 --out results_image_model`

**Limit:** this model has only ever seen synthetic RR data. Demo results prove the plumbing works, not clinical accuracy.
Train on real data (e.g. PhysioNet/CinC 2017 or Icentia11k) with `--data icentia` before trusting it on real ECGs.

## Image in -> verdict out (no dataset needed)
```bash
python make_demo_images.py                          # fake ECG-paper pictures -> demo_images/
python predict_image.py demo_images/afib_0.png --out result.png
python predict_image.py my_strip.jpg --seconds 10   # your own single-lead strip
```
`results_image_model/` is a CNN->BiLSTM trained on **synthetic** RR data with an 8-interval window
(`python train.py --data synthetic --window-beats 8 --stride-beats 2 --out results_image_model`), because a 10 s
strip holds only ~10-15 beats (the 30-beat model cannot run on it). Scores on synthetic data prove the code runs, not clinical accuracy.
Retrain on Icentia11k with the same `--window-beats 8` before trusting it on real ECGs.
