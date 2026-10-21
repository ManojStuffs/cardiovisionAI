"""CardioVision AI — Clinical ECG & Arrhythmia Detection Space.

Model: adilsaleem/ecg-image-multilabel-classification (Vision Transformer)
Fine-tuned on ECG Lead images for multi-condition arrhythmia detection:
  - AFIB: Atrial Fibrillation
  - NORM: Normal Sinus Rhythm
  - MI: Myocardial Infarction
  - STTC: ST/T-Wave Changes
  - CD: Conduction Disturbance

Integrates deep neural ViT inference with signal processing (Pan-Tompkins R-peak detector)
and RR-interval telemetry.
"""
from __future__ import annotations
import os
import io
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional ZeroGPU compatibility on Hugging Face Spaces
try:
    import spaces
except ImportError:
    spaces = None

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import gradio as gr

from hf_ecg_model import run_hybrid_analysis, CONDITION_INFO


def create_ecg_plot(telemetry: Dict[str, Any]) -> Optional[plt.Figure]:
    """Render digitized ECG strip with highlighted R-peaks."""
    waveform = telemetry.get("waveform_preview")
    if not waveform or not waveform.get("times") or not waveform.get("values"):
        return None

    times = np.array(waveform["times"])
    values = np.array(waveform["values"])
    peak_times = set(waveform.get("peak_indices", []))

    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=150)
    fig.patch.set_facecolor("#0b0f19")
    ax.set_facecolor("#0f172a")

    # ECG paper grid styling
    ax.grid(True, which="both", color="#1e293b", linestyle="-", linewidth=0.7, alpha=0.8)
    ax.minorticks_on()
    ax.grid(True, which="minor", color="#162032", linestyle=":", linewidth=0.4, alpha=0.5)

    # Plot ECG waveform
    ax.plot(times, values, color="#00f0ff", linewidth=1.5, label="Filtered Lead Trace", zorder=2)

    # Highlight R-peaks
    if peak_times:
        p_times = []
        p_vals = []
        for p_t in peak_times:
            # Find closest sample index
            idx = int(np.argmin(np.abs(times - p_t)))
            if idx < len(values):
                p_times.append(times[idx])
                p_vals.append(values[idx])

        if p_times:
            ax.scatter(p_times, p_vals, color="#ff0055", s=45, zorder=3, edgecolors="#ffffff", linewidth=0.8, label="Detected R-peaks")

    ax.set_title("Digitized Rhythm Strip & Pan-Tompkins Peak Alignment", color="#e2e8f0", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Time (seconds)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("Normalized Amplitude", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#64748b", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#334155")

    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8, loc="upper right")
    plt.tight_layout()
    return fig


def predict_ecg(image: Image.Image, seconds: float = 10.0) -> Tuple[str, Dict[str, float], Optional[plt.Figure], str]:
    """Run diagnostic classification and waveform digitization on an ECG strip image.

    Args:
        image: PIL image of a single-lead ECG rhythm strip.
        seconds: Trace duration in seconds (default: 10.0s).

    Returns:
        verdict_markdown: Clinical assessment headline and status banner.
        label_scores: Dictionary of condition probabilities for gr.Label.
        plot_fig: Matplotlib figure showing digitized waveform and R-peaks.
        telemetry_md: Formatted diagnostic metrics table.
    """
    if image is None:
        return "⚠️ Please upload an ECG image or select one of the examples below.", {}, None, ""

    # Convert PIL Image to PNG bytes
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    result = run_hybrid_analysis(image_bytes, seconds=seconds)
    if result.get("status") != "success":
        return f"❌ Analysis Error: {result.get('error', 'Unknown error')}", {}, None, ""

    is_afib = result.get("is_afib", False)
    afib_pct = result.get("afib_percentage", 0.0)
    confidence = result.get("confidence", 0.0)
    engine = result.get("engine", "Neural ViT")
    top_condition = result.get("top_condition", "NORM")

    # Generate Verdict Banner
    if is_afib:
        banner = (
            f"<div style='background: linear-gradient(135deg, rgba(255, 0, 85, 0.2), rgba(139, 0, 0, 0.3)); "
            f"border: 1px solid #ff0055; border-radius: 8px; padding: 16px; margin-bottom: 12px;'>"
            f"<h2 style='color: #ff3366; margin: 0;'>🚨 ATRIAL FIBRILLATION DETECTED</h2>"
            f"<p style='color: #fca5a5; margin: 4px 0 0 0; font-size: 14px;'>AFib Probability: <b>{afib_pct:.1f}%</b> | "
            f"Primary Arrhythmia Pattern: <b>{top_condition}</b> | Engine: <i>{engine}</i></p>"
            f"</div>"
        )
    else:
        banner = (
            f"<div style='background: linear-gradient(135deg, rgba(0, 230, 118, 0.15), rgba(0, 100, 50, 0.25)); "
            f"border: 1px solid #00e676; border-radius: 8px; padding: 16px; margin-bottom: 12px;'>"
            f"<h2 style='color: #00e676; margin: 0;'>✅ NO ATRIAL FIBRILLATION DETECTED</h2>"
            f"<p style='color: #86efac; margin: 4px 0 0 0; font-size: 14px;'>Normal Rhythm Match: <b>{confidence:.1f}%</b> | "
            f"AFib Probability: <b>{afib_pct:.1f}%</b> | Engine: <i>{engine}</i></p>"
            f"</div>"
        )

    # Condition probabilities for Gradio Label
    predictions = result.get("predictions", [])
    label_scores = {}
    for p in predictions:
        display_label = f"{p['title']} ({p['label']})"
        label_scores[display_label] = float(p.get("score", 0.0))

    # Waveform plot
    telemetry = result.get("telemetry", {})
    plot_fig = create_ecg_plot(telemetry)

    # Telemetry details
    n_beats = telemetry.get("n_beats", 0)
    rr_cv = telemetry.get("rr_cv", 0.0)
    sampling_rate = telemetry.get("sampling_rate", 250.0)
    duration = telemetry.get("signal_duration_sec", seconds)

    telemetry_md = f"""
| Metric | Value | Reference / Clinical Meaning |
|---|---|---|
| **Primary Condition** | `{top_condition}` | Model classification |
| **AFib Confidence** | `{afib_pct:.1f}%` | Neural probability score |
| **Detected R-Peaks** | `{n_beats} beats` | Pan-Tompkins QRS detector |
| **RR Variability (CV)** | `{rr_cv:.3f}` | RR std / mean (AFib typically > 0.15) |
| **Resampled Rate** | `{sampling_rate} Hz` | Standardized band-passed ECG rate |
| **Strip Duration** | `{duration} s` | Analyzed duration window |
| **Inference Engine** | `{engine}` | Deep Vision Transformer |
"""

    return banner, label_scores, plot_fig, telemetry_md


# ZeroGPU decorator when running on Hugging Face Spaces with ZeroGPU
if spaces is not None:
    predict_ecg = spaces.GPU(duration=30)(predict_ecg)

# Gradio Interface Construction
theme = gr.themes.Soft(
    primary_hue="cyan",
    secondary_hue="rose",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Plus Jakarta Sans"), "sans-serif"]
)

with gr.Blocks(title="CardioVision AI — AFib Detection") as demo:
    gr.HTML("""
    <div style="text-align: center; padding: 15px 0;">
        <h1 style="font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #00f0ff, #7000ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 6px;">
            CardioVision AI
        </h1>
        <p style="font-size: 1.05rem; color: #94a3b8; max-width: 650px; margin: 0 auto;">
            Deep learning cardiac electrophysiology platform powered by Vision Transformers (ViT) and signal processing for real-time Atrial Fibrillation detection.
        </p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=5):
            input_image = gr.Image(type="pil", label="ECG Rhythm Strip (Image)", height=280)
            seconds_slider = gr.Slider(minimum=5.0, maximum=30.0, value=10.0, step=1.0, label="Rhythm Strip Duration (Seconds)")
            analyze_btn = gr.Button("⚡ Analyze Cardiac Rhythm", variant="primary", size="lg")

            # Reference Samples
            examples_dir = PROJECT_ROOT / "demo_images"
            if examples_dir.exists():
                example_files = sorted([str(f) for f in examples_dir.glob("*.png")])[:4]
                if example_files:
                    gr.Examples(
                        examples=example_files,
                        inputs=input_image,
                        label="Reference ECG Strips (Click to Load)"
                    )

        with gr.Column(scale=7):
            verdict_output = gr.HTML(label="Diagnostic Assessment")
            label_output = gr.Label(num_top_classes=5, label="Arrhythmia Multi-Label Classification")
            plot_output = gr.Plot(label="ECG Waveform & Pan-Tompkins Peak Alignment")
            telemetry_output = gr.Markdown(label="Clinical Telemetry")

    analyze_btn.click(
        fn=predict_ecg,
        inputs=[input_image, seconds_slider],
        outputs=[verdict_output, label_output, plot_output, telemetry_output]
    )

    gr.Markdown("""
    ---
    **Model Architecture:** Vision Transformer (`adilsaleem/ecg-image-multilabel-classification`) fine-tuned on ECG images with Pan-Tompkins QRS R-peak telemetry.
    *Disclaimer: Research and educational demonstration platform. Not intended as a substitute for professional clinical medical advice.*
    """)

if __name__ == "__main__":
    demo.launch(theme=theme, mcp_server=True)
