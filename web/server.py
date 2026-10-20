"""Flask Web Application for Clinical ECG Atrial Fibrillation & Arrhythmia Detection.

Serves an interactive web application allowing clinicians and users to upload ECG images,
inspect detected cardiac rhythms, and obtain deep multi-label cardiac diagnostic predictions.
"""
from __future__ import annotations
import os
import sys
import io
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_cors import CORS
from hf_ecg_model import run_hybrid_analysis, is_torch_ready

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

DEMO_DIR = PROJECT_ROOT / "demo_images"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/system-status")
def system_status():
    return jsonify({
        "status": "ready",
        "model_name": "CardioVision DeepNet ViT",
        "torch_available": is_torch_ready(),
        "backend": "Local Neural Engine" if is_torch_ready() else "Cloud Neural Engine"
    })


@app.route("/api/samples")
def list_samples():
    """List available demo ECG images with labels."""
    samples = []
    if DEMO_DIR.exists():
        for file in sorted(DEMO_DIR.glob("*.png")):
            is_afib = "afib" in file.name.lower()
            samples.append({
                "filename": file.name,
                "label": "Atrial Fibrillation (AFib)" if is_afib else "Normal Sinus Rhythm",
                "is_afib": is_afib,
                "url": f"/api/sample-image/{file.name}"
            })
    return jsonify(samples)


@app.route("/api/sample-image/<path:filename>")
def get_sample_image(filename):
    """Serve a sample ECG image."""
    safe_path = (DEMO_DIR / filename).resolve()
    if not safe_path.is_file() or safe_path.parent != DEMO_DIR.resolve():
        return jsonify({"error": "File not found"}), 404
    return send_file(safe_path, mimetype="image/png")


@app.route("/api/predict", methods=["POST"])
def predict():
    """Analyze an uploaded ECG image."""
    seconds = float(request.form.get("seconds", 10.0))

    # Check if a file was uploaded
    if "file" in request.files and request.files["file"].filename != "":
        file = request.files["file"]
        image_bytes = file.read()
    # Check if a sample was selected
    elif "sample_name" in request.form:
        sample_path = DEMO_DIR / request.form["sample_name"]
        if not sample_path.exists():
            return jsonify({"error": f"Sample {request.form['sample_name']} not found"}), 404
        with open(sample_path, "rb") as f:
            image_bytes = f.read()
    else:
        return jsonify({"error": "No image file or sample provided."}), 400

    try:
        results = run_hybrid_analysis(image_bytes, seconds=seconds)
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Inference failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==================================================")
    print(f"  CardioVision AI — Clinical ECG Diagnostic Platform")
    print(f"  URL: http://127.0.0.1:{port}")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
