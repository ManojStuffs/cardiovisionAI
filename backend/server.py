"""CardioVision AI — Dedicated Backend REST API Server.

Provides a clean, decoupled REST API for deep cardiac arrhythmia and Atrial Fibrillation
detection using the pretrained Vision Transformer model.
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

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from hf_ecg_model import run_hybrid_analysis, is_torch_ready

app = Flask(__name__)
# Enable CORS for all routes so React + Vite frontend can communicate without friction
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max

DEMO_DIR = PROJECT_ROOT / "demo_images"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@app.after_request
def add_security_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/system-status", methods=["GET"])
def system_status():
    """Health check and model status."""
    return jsonify({
        "status": "ready",
        "model_name": "CardioVision DeepNet ViT",
        "architecture": "Vision Transformer (ViT)",
        "torch_available": is_torch_ready(),
        "backend": "Local Neural Engine" if is_torch_ready() else "Cloud Neural Engine"
    })


@app.route("/api/samples", methods=["GET"])
def list_samples():
    """List available reference ECG images."""
    samples = []
    if DEMO_DIR.exists():
        files = sorted(DEMO_DIR.glob("*.png"))
        for idx, file in enumerate(files):
            is_afib = "afib" in file.name.lower()
            clean_name = file.stem.replace("afib_", "AFib Case ").replace("normal_", "Normal Sinus ")
            if "case" not in clean_name.lower() and "sinus" not in clean_name.lower():
                clean_name = f"Case {idx + 1}"

            samples.append({
                "filename": file.name,
                "display_name": clean_name.title(),
                "label": "Atrial Fibrillation (AFib)" if is_afib else "Normal Sinus Rhythm",
                "is_afib": is_afib,
                "url": f"/api/sample-image/{file.name}"
            })
    return jsonify(samples)


@app.route("/api/sample-image/<path:filename>", methods=["GET"])
def get_sample_image(filename):
    """Serve reference ECG image."""
    safe_path = (DEMO_DIR / filename).resolve()
    if not safe_path.is_file() or safe_path.parent != DEMO_DIR.resolve():
        return jsonify({"error": "Reference image not found"}), 404
    return send_file(safe_path, mimetype="image/png")


@app.route("/api/predict", methods=["POST"])
def predict():
    """Analyze an uploaded ECG trace image."""
    seconds = float(request.form.get("seconds", 10.0))

    if "file" in request.files and request.files["file"].filename != "":
        file = request.files["file"]
        image_bytes = file.read()
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
        
        # Ensure no heart rate telemetry is in the response
        if "telemetry" in results and isinstance(results["telemetry"], dict):
            results["telemetry"].pop("heart_rate_bpm", None)
            
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Diagnostic analysis failed: {str(e)}"}), 500


# Serve React static assets and index.html for Single-Page Application (SPA)
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    """Serve React frontend from frontend/dist."""
    if path.startswith("api/"):
        return jsonify({"error": "API endpoint not found"}), 404

    safe_dist = FRONTEND_DIST.resolve()
    target_file = (FRONTEND_DIST / path).resolve()

    if path != "" and target_file.is_file() and safe_dist in target_file.parents:
        return send_from_directory(str(safe_dist), path)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(str(safe_dist), "index.html")

    return jsonify({
        "status": "ready",
        "message": "CardioVision API is running. Build frontend/dist to view the web interface."
    })


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==================================================")
    print(f"  CardioVision AI — Production Ready Web Application")
    print(f"  Serving locally & externally on: http://{host}:{port}")
    print(f"==================================================\n")
    app.run(host=host, port=port, debug=False)
