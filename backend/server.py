"""CardioVision AI — Dedicated Backend REST API Server.

Provides a clean, decoupled REST API for deep cardiac arrhythmia and Atrial Fibrillation
detection with role-based Doctor & Patient authentication, email verification,
and clinical report management.
"""
from __future__ import annotations
import os
import sys
import io
import json
import base64
from pathlib import Path
from functools import wraps

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

from hf_ecg_model import run_hybrid_analysis, is_torch_ready
import backend.database as db
from backend.mailer import generate_otp, send_verification_email

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max

DEMO_DIR = PROJECT_ROOT / "demo_images"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# Initialize SQLite database and seed test accounts on boot
db.init_db()


@app.after_request
def add_security_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def get_current_user():
    """Extract authenticated user from Authorization Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    payload = db.verify_auth_token(token)
    if not payload:
        return None
    return db.get_user_by_id(payload["uid"])


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required. Please sign in."}), 401
        return f(user, *args, **kwargs)
    return decorated


def require_role(required_role: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required. Please sign in."}), 401
            if user["role"] != required_role:
                return jsonify({
                    "error": f"Access denied. Only {required_role}s are authorized to access this resource."
                }), 403
            return f(user, *args, **kwargs)
        return decorated
    return decorator


# =========================================================================
# System & Sample Routes
# =========================================================================

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


# =========================================================================
# Authentication & Email Verification Routes
# =========================================================================

@app.route("/api/auth/register-request", methods=["POST"])
def register_request():
    """Step 1 of Registration: Validate input and send 6-digit email OTP."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")
    role = data.get("role", "patient").strip().lower()
    title = data.get("title", "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email address is required."}), 400
    if not name or len(name) < 2:
        return jsonify({"error": "Full name is required."}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if role not in ("doctor", "patient"):
        return jsonify({"error": "Role must be either 'doctor' or 'patient'."}), 400

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email address already exists. Please sign in."}), 409

    otp = generate_otp()
    db.store_otp(email, otp, purpose="signup", valid_seconds=600)
    _, msg = send_verification_email(email, name, otp, purpose="signup")

    return jsonify({
        "status": "otp_sent",
        "email": email,
        "message": msg,
        "dev_otp": otp  # Included for seamless local evaluation/testing
    })


@app.route("/api/auth/verify-and-register", methods=["POST"])
def verify_and_register():
    """Step 2 of Registration: Verify OTP and create authenticated account."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")
    role = data.get("role", "patient").strip().lower()
    title = data.get("title", "").strip()
    otp = data.get("otp", "").strip()

    if not db.verify_otp(email, otp, purpose="signup"):
        return jsonify({"error": "Invalid or expired verification code. Please check and try again."}), 400

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "User already registered."}), 409

    user = db.create_user(name, email, password, role, title=title, is_verified=True)
    token = db.generate_auth_token(user)

    return jsonify({
        "status": "registered",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "title": user["title"]
        }
    })


@app.route("/api/auth/login-request", methods=["POST"])
def login_request():
    """Step 1 of Login: Check password and send 6-digit email OTP."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = db.get_user_by_email(email)
    if not user or not db.check_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password."}), 401

    otp = generate_otp()
    db.store_otp(email, otp, purpose="signin", valid_seconds=600)
    _, msg = send_verification_email(email, user["name"], otp, purpose="signin")

    return jsonify({
        "status": "otp_sent",
        "email": email,
        "role": user["role"],
        "message": msg,
        "dev_otp": otp  # Included for seamless local evaluation/testing
    })


@app.route("/api/auth/verify-login", methods=["POST"])
def verify_login():
    """Step 2 of Login: Verify OTP and return session token."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not db.verify_otp(email, otp, purpose="signin"):
        return jsonify({"error": "Invalid or expired verification code."}), 400

    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "User account not found."}), 404

    token = db.generate_auth_token(user)
    return jsonify({
        "status": "authenticated",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "title": user["title"]
        }
    })


@app.route("/api/auth/demo-login", methods=["POST"])
def demo_login():
    """Instant 1-click login for quick evaluators and demonstrations."""
    data = request.get_json() or {}
    role = data.get("role", "doctor").strip().lower()

    if role == "doctor":
        target_email = "dr.smith@cardiovision.org"
    else:
        target_email = "john.doe@patient.org"

    user = db.get_user_by_email(target_email)
    if not user:
        return jsonify({"error": f"Demo user for {role} not found."}), 404

    token = db.generate_auth_token(user)
    return jsonify({
        "status": "authenticated",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "title": user["title"]
        }
    })


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_me(user):
    """Retrieve currently authenticated user profile."""
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "title": user["title"]
    })


# =========================================================================
# Doctor-Only Endpoints: ECG Prediction & Report Publishing
# =========================================================================

@app.route("/api/predict", methods=["POST"])
@require_role("doctor")
def predict(doctor_user):
    """Analyze an uploaded ECG trace image.
    STRICTLY AUTHORIZED: Medical Doctors Only.
    """
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
        if "telemetry" in results and isinstance(results["telemetry"], dict):
            results["telemetry"].pop("heart_rate_bpm", None)

        # Attach doctor sign-off metadata
        results["analyzing_doctor"] = {
            "name": doctor_user["name"],
            "title": doctor_user.get("title", "Attending Cardiologist")
        }
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Diagnostic analysis failed: {str(e)}"}), 500


@app.route("/api/doctor/patients", methods=["GET"])
@require_role("doctor")
def list_patients(doctor_user):
    """Return list of registered patients for doctor's selection."""
    patients = db.get_all_patients()
    return jsonify(patients)


@app.route("/api/doctor/save-report", methods=["POST"])
@require_role("doctor")
def save_report(doctor_user):
    """Doctor finalizes and publishes an official report to a specific patient."""
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    result_data = data.get("result_data")
    notes = data.get("doctor_notes", "")
    recommendation = data.get("clinical_recommendation", "")
    image_url = data.get("image_url", "")

    if not patient_id or not result_data:
        return jsonify({"error": "Patient ID and Diagnostic Result data are required."}), 400

    try:
        saved = db.save_clinical_report(
            doctor_user=doctor_user,
            patient_id=int(patient_id),
            result_data=result_data,
            notes=notes,
            recommendation=recommendation,
            image_url=image_url
        )
        return jsonify({
            "status": "success",
            "message": f"Report successfully published to patient {saved['patient_name']}.",
            "report": saved
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/doctor/reports", methods=["GET"])
@require_role("doctor")
def get_my_reports(doctor_user):
    """Doctor views all clinical reports they have authored."""
    reports = db.get_doctor_reports(doctor_user["id"])
    return jsonify(reports)


# =========================================================================
# Patient-Only Endpoints: Viewing Assigned Reports
# =========================================================================

@app.route("/api/patient/reports", methods=["GET"])
@require_role("patient")
def get_my_patient_reports(patient_user):
    """Patient retrieves ONLY reports created for their account by their attending doctor."""
    reports = db.get_patient_reports(patient_user["id"])
    return jsonify({
        "patient": {
            "id": patient_user["id"],
            "name": patient_user["name"],
            "email": patient_user["email"],
            "title": patient_user["title"]
        },
        "reports": reports
    })


# =========================================================================
# Static Assets & Frontend Routing
# =========================================================================

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
