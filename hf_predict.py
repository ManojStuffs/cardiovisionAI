"""Command-line interface to run Hugging Face ECG ViT inference on any ECG image.

Usage:
  python hf_predict.py demo_images/afib_0.png
  python hf_predict.py demo_images/normal_0.png --seconds 10
  python hf_predict.py path/to/my_ecg.jpg
"""
import sys
import json
import argparse
from pathlib import Path
from hf_ecg_model import run_hybrid_analysis


def main():
    parser = argparse.ArgumentParser(description="Classify ECG image using Hugging Face Vision Transformer model.")
    parser.add_argument("image", help="Path to ECG image file (PNG, JPG, TIFF)")
    parser.add_argument("--seconds", type=float, default=10.0, help="Duration in seconds (default: 10.0)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Error: File '{args.image}' not found.")
        sys.exit(1)

    print(f"\nAnalyzing '{img_path.name}' using Hugging Face ECG Model...")
    res = run_hybrid_analysis(img_path, seconds=args.seconds)

    if args.json:
        # Don't print large waveform points in terminal JSON
        summary = dict(res)
        if "telemetry" in summary and "waveform_preview" in summary["telemetry"]:
            summary["telemetry"]["waveform_preview"] = "[Waveform points omitted]"
        print(json.dumps(summary, indent=2))
        return

    print("=" * 60)
    print(f"  VERDICT:       {res['verdict']}")
    print(f"  TOP DIAGNOSIS: {res['top_condition']} ({res['confidence']}%)")
    print(f"  AFIB RISK:     {res['afib_percentage']}%")
    print(f"  INFERENCE VIA: {res['engine']}")
    print("=" * 60)

    telem = res.get("telemetry", {})
    if telem and telem.get("heart_rate_bpm"):
        print(f"  Heart Rate:    ~{telem['heart_rate_bpm']} BPM")
        print(f"  Beats Count:   {telem['n_beats']} detected")
        print(f"  RR Variability (CV): {telem['rr_cv']}")
        print("-" * 60)

    print("Condition Breakdown (Hugging Face ViT):")
    for p in res.get("predictions", []):
        bar_len = int(p['percentage'] / 4)
        bar = "#" * bar_len + "-" * (25 - bar_len)
        print(f"  [{p['label']:<4}] {p['percentage']:5.1f}% |{bar}| {p['title']} ({p['urgency']})")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
