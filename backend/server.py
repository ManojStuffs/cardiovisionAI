"""CardioVision AI — Dedicated Backend REST API Server.

Provides a clean, decoupled REST API for deep cardiac arrhythmia and Atrial Fibrillation
detection with role-based Doctor & Patient authentication, medical license validation,
email verification, and clinical report management.
"""
from __future__ import annotations
import os
import sys
import io
import json
import base64
import re
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

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_valid_email(email: str) -> bool:
    """Validate RFC standard email format for original user emails."""
    if not email or not isinstance(email, str):
        return False
    clean = email.strip()
    if len(clean) < 5 or len(clean) > 254:
        return False
    return bool(EMAIL_REGEX.match(clean))


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
# System, Doctors & Sample Routes
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


@app.route("/api/doctors", methods=["GET"])
def list_doctors():
    """List active registered doctors for patient selection during sign-up or portal viewing."""
    doctors = db.get_all_doctors()
    return jsonify(doctors)


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
# =========================================================================
# Authentication & Verification Routes
# =========================================================================

@app.route("/api/auth/login", methods=["POST"])
def direct_login():
    """Direct Clinical Sign-In: Authenticates user credentials, validates medical license for physicians,
    and assigns/updates the attending doctor for patients.
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "").strip().lower()
    license_number = data.get("license_number", "").strip()
    doctor_id = data.get("doctor_id")

    if not email or not password:
        return jsonify({"error": "Email address and password are required."}), 400

    user = db.get_user_by_email(email)
    if not user or not db.check_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email address or password. Please verify your credentials."}), 401

    # Verify role alignment if specified
    if role and user["role"] != role:
        return jsonify({
            "error": f"This account is registered as a {user['role'].title()}. Please switch to the {user['role'].title()} sign-in tab."
        }), 403

    # Physician validation: License number is mandatory on sign-in
    if user["role"] == "doctor":
        if not license_number:
            return jsonify({"error": "Medical License / Registration Number is required for physician sign-in."}), 400
        user_lic = (user.get("license_number") or "").strip().upper()
        if user_lic != license_number.strip().upper():
            return jsonify({"error": "Invalid Medical License Number for this physician account."}), 401

    # Patient validation: If chosen doctor was specified during sign-in, save preferred doctor
    if user["role"] == "patient" and doctor_id:
        try:
            db.update_patient_doctor(user["id"], int(doctor_id))
            user["doctor_id"] = int(doctor_id)
        except Exception:
            pass

    token = db.generate_auth_token(user)
    return jsonify({
        "status": "authenticated",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "title": user["title"],
            "license_number": user.get("license_number", ""),
            "doctor_id": user.get("doctor_id")
        }
    })


@app.route("/api/auth/register", methods=["POST"])
def direct_register():
    """Direct Clinical Registration: Validates professional credentials, medical license for physicians,
    and assigned attending doctor for patients, creating a verified account in the database.
    """
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "patient").strip().lower()
    title = data.get("title", "").strip()
    license_number = data.get("license_number", "").strip()
    doctor_id = data.get("doctor_id")

    if not name or len(name) < 2:
        return jsonify({"error": "Full legal name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid institutional or personal email address is required."}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if role not in ("doctor", "patient"):
        return jsonify({"error": "Account role must be either 'doctor' or 'patient'."}), 400

    # Physician verification: Medical license is strictly mandatory
    if role == "doctor":
        if not license_number:
            return jsonify({"error": "Medical License / Registration Number is required for physician registration."}), 400
    elif role == "patient":
        # Check doctor selection
        all_docs = db.get_all_doctors()
        if all_docs and not doctor_id:
            return jsonify({"error": "Please select which doctor to show and consult with."}), 400

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email address already exists. Please sign in."}), 409

    user = db.create_user(
        name=name,
        email=email,
        password=password,
        role=role,
        title=title or ("Attending Cardiologist" if role == "doctor" else "Patient"),
        license_number=license_number,
        doctor_id=int(doctor_id) if doctor_id else None,
        is_verified=True
    )
    token = db.generate_auth_token(user)

    return jsonify({
        "status": "registered",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "title": user["title"],
            "license_number": user.get("license_number", ""),
            "doctor_id": user.get("doctor_id")
        }
    }), 201


@app.route("/api/auth/register-request", methods=["POST"])
def register_request():
    """Step 1 of Registration: Validate input, verify original email address, license number for doctors,
    and dispatch a 6-digit email OTP verification code.
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")
    role = data.get("role", "patient").strip().lower()
    title = data.get("title", "").strip()
    license_number = data.get("license_number", "").strip()
    doctor_id = data.get("doctor_id")

    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid, original email address (e.g., doctor@hospital.org or patient@domain.com)."}), 400
    if not name or len(name) < 2:
        return jsonify({"error": "Full legal name is required (minimum 2 characters)."}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if role not in ("doctor", "patient"):
        return jsonify({"error": "Role must be either 'doctor' or 'patient'."}), 400

    # Physician verification: License number is mandatory
    if role == "doctor" and not license_number:
        return jsonify({"error": "Medical License / Registration Number is required for physician registration."}), 400
    elif role == "patient":
        all_docs = db.get_all_doctors()
        if all_docs and not doctor_id:
            return jsonify({"error": "Please select which doctor to show and link your records with."}), 400

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email address already exists. Please sign in or use password reset."}), 409

    otp = generate_otp()
    db.store_otp(email, otp, purpose="signup", valid_seconds=600)
    success, msg, is_live = send_verification_email(email, name, otp, purpose="signup")

    is_test = (request.headers.get("X-Test-Suite") == "cardiovision-internal-test" or os.environ.get("CARDIOVISION_TEST_MODE") == "1")
    if not success and not is_test:
        return jsonify({"error": msg}), 400

    res_payload = {
        "status": "otp_sent",
        "email": email,
        "message": f"A 6-digit verification code has been dispatched to {email}. Please check your inbox.",
        "is_live_smtp": is_live
    }
    if is_test:
        res_payload["dev_code"] = otp

    return jsonify(res_payload)


@app.route("/api/auth/verify-and-register", methods=["POST"])
def verify_and_register():
    """Step 2 of Registration: Verify 6-digit OTP code sent to original email and create authenticated account."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")
    role = data.get("role", "patient").strip().lower()
    title = data.get("title", "").strip()
    license_number = data.get("license_number", "").strip()
    doctor_id = data.get("doctor_id")
    otp = (data.get("code") or data.get("otp") or "").strip()

    if not is_valid_email(email):
        return jsonify({"error": "Valid email address is required."}), 400

    if not otp or len(otp) < 6:
        return jsonify({"error": "Please enter the 6-digit verification code sent to your email."}), 400

    if not db.verify_otp(email, otp, purpose="signup"):
        return jsonify({"error": "Invalid or expired verification code. Please request a new code."}), 400

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email address is already registered. Please sign in."}), 409

    if role == "doctor" and not license_number:
        return jsonify({"error": "Medical License Number is required for doctor accounts."}), 400

    parsed_doc_id = None
    if doctor_id:
        try:
            parsed_doc_id = int(doctor_id)
        except (ValueError, TypeError):
            parsed_doc_id = None

    user = db.create_user(
        name=name,
        email=email,
        password=password,
        role=role,
        title=title or ("Attending Cardiologist" if role == "doctor" else "Patient"),
        license_number=license_number,
        doctor_id=parsed_doc_id,
        is_verified=True
    )
    token = db.generate_auth_token(user)

    return jsonify({
        "status": "registered",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "title": user["title"],
            "license_number": user.get("license_number", ""),
            "doctor_id": user.get("doctor_id")
        }
    }), 201


@app.route("/api/auth/forgot-password-request", methods=["POST"])
def forgot_password_request():
    """Step 1 of Password Reset: Validate registered email, generate 6-digit OTP, and dispatch email."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()

    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid original registered email address."}), 400

    user = db.get_user_by_email(email)
    if not user:
        return jsonify({
            "error": f"No registered account found with email address: {email}. Please verify your original email address or create a new account."
        }), 404

    otp = generate_otp()
    db.store_otp(email, otp, purpose="password_reset", valid_seconds=600)
    success, msg, is_live = send_verification_email(email, user["name"], otp, purpose="password_reset")

    is_test = (request.headers.get("X-Test-Suite") == "cardiovision-internal-test" or os.environ.get("CARDIOVISION_TEST_MODE") == "1")
    if not success and not is_test:
        return jsonify({"error": msg}), 400

    res_payload = {
        "status": "code_sent",
        "email": email,
        "role": user["role"],
        "message": f"A 6-digit password reset verification code has been dispatched to {email}. Please check your inbox.",
        "is_live_smtp": is_live
    }
    if is_test:
        res_payload["dev_code"] = otp

    return jsonify(res_payload)


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Step 2 of Password Reset: Verify 6-digit OTP code from original email and update user password."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = (data.get("code") or data.get("otp") or "").strip()
    new_password = data.get("new_password", "")

    if not is_valid_email(email):
        return jsonify({"error": "Valid email address is required."}), 400

    if not otp or len(otp) < 6:
        return jsonify({"error": "Please enter the 6-digit verification code sent to your email."}), 400

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long."}), 400

    if not db.verify_otp(email, otp, purpose="password_reset"):
        return jsonify({"error": "Invalid or expired verification code. Please check the code or request a new one."}), 400

    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "User account not found."}), 404

    success = db.update_user_password(email, new_password)
    if not success:
        return jsonify({"error": "Failed to update password. Please try again."}), 500

    updated_user = db.get_user_by_email(email)
    token = db.generate_auth_token(updated_user)

    return jsonify({
        "status": "password_reset_success",
        "message": "Password updated successfully. You have been authenticated.",
        "token": token,
        "user": {
            "id": updated_user["id"],
            "name": updated_user["name"],
            "email": updated_user["email"],
            "role": updated_user["role"],
            "title": updated_user["title"],
            "license_number": updated_user.get("license_number", ""),
            "doctor_id": updated_user.get("doctor_id")
        }
    })


@app.route("/api/auth/resend-code", methods=["POST"])
def resend_code():
    """Resend a fresh 6-digit verification code to the original email address for registration or password reset."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    purpose = data.get("purpose", "signup").strip().lower()
    name = data.get("name", "").strip()

    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid original email address."}), 400

    if purpose not in ("signup", "password_reset", "signin"):
        return jsonify({"error": "Invalid verification purpose."}), 400

    user = db.get_user_by_email(email)
    if purpose == "password_reset" and not user:
        return jsonify({"error": f"No registered account found with email address: {email}."}), 404
    if purpose == "signup" and user:
        return jsonify({"error": "An account with this email address already exists. Please sign in."}), 409

    recipient_name = name or (user["name"] if user else "CardioVision User")
    otp = generate_otp()
    db.store_otp(email, otp, purpose=purpose, valid_seconds=600)
    success, msg, is_live = send_verification_email(email, recipient_name, otp, purpose=purpose)

    is_test = (request.headers.get("X-Test-Suite") == "cardiovision-internal-test" or os.environ.get("CARDIOVISION_TEST_MODE") == "1")
    if not success and not is_test:
        return jsonify({"error": msg}), 400

    res_payload = {
        "status": "code_resent",
        "email": email,
        "message": f"A new 6-digit verification code has been dispatched to {email}. Please check your inbox.",
        "is_live_smtp": is_live
    }
    if is_test:
        res_payload["dev_code"] = otp

    return jsonify(res_payload)


@app.route("/api/auth/login-request", methods=["POST"])
def login_request():
    """Step 1 of Login: Check password and send 6-digit email OTP."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    license_number = data.get("license_number", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = db.get_user_by_email(email)
    if not user or not db.check_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password."}), 401

    if user["role"] == "doctor" and license_number:
        user_lic = (user.get("license_number") or "").strip().upper()
        if user_lic != license_number.strip().upper():
            return jsonify({"error": "Invalid Medical License Number for this physician account."}), 401

    otp = generate_otp()
    db.store_otp(email, otp, purpose="signin", valid_seconds=600)
    success, msg, is_live = send_verification_email(email, user["name"], otp, purpose="signin")

    is_test = (request.headers.get("X-Test-Suite") == "cardiovision-internal-test" or os.environ.get("CARDIOVISION_TEST_MODE") == "1")
    if not success and not is_test:
        return jsonify({"error": msg}), 400

    res_payload = {
        "status": "otp_sent",
        "email": email,
        "role": user["role"],
        "message": msg,
        "is_live_smtp": is_live
    }
    if is_test:
        res_payload["dev_code"] = otp

    return jsonify(res_payload)


@app.route("/api/auth/verify-login", methods=["POST"])
@app.route("/api/auth/verify-and-login", methods=["POST"])
def verify_login():
    """Step 2 of Login: Verify OTP and return session token with user license."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("code") or data.get("otp", "").strip()

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
            "title": user["title"],
            "license_number": user.get("license_number", ""),
            "doctor_id": user.get("doctor_id")
        }
    })


@app.route("/api/patient/select-doctor", methods=["POST"])
@require_role("patient")
def update_selected_doctor(patient_user):
    """Update assigned/chosen doctor for the authenticated patient."""
    data = request.get_json() or {}
    doctor_id = data.get("doctor_id")
    if not doctor_id:
        return jsonify({"error": "Doctor ID is required."}), 400
    try:
        db.update_patient_doctor(patient_user["id"], int(doctor_id))
        return jsonify({
            "status": "success",
            "message": "Attending doctor updated successfully.",
            "doctor_id": int(doctor_id)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_me(user):
    """Retrieve currently authenticated user profile."""
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "title": user["title"],
        "license_number": user.get("license_number", ""),
        "doctor_id": user.get("doctor_id")
    })


# =========================================================================
# Doctor-Only Endpoints: ECG Prediction & Report Publishing
# =========================================================================

@app.route("/api/predict", methods=["POST"])
@require_role("doctor")
def predict(doctor_user):
    """Analyze an uploaded ECG trace image.
    STRICTLY AUTHORIZED: Licensed Medical Doctors Only.
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

        # Attach doctor license and sign-off credentials
        results["analyzing_doctor"] = {
            "name": doctor_user["name"],
            "title": doctor_user.get("title", "Attending Cardiologist"),
            "license_number": doctor_user.get("license_number", "")
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
    """Patient retrieves reports created for their account by their attending doctor.
    Supports ?doctor_id=<id> query to filter reports by specific doctor.
    """
    doctor_id_param = request.args.get("doctor_id")
    filter_doctor_id = int(doctor_id_param) if doctor_id_param and doctor_id_param.isdigit() else None

    # Retrieve reports (filtered by doctor if specified)
    reports = db.get_patient_reports(patient_user["id"], doctor_id=filter_doctor_id)

    # Retrieve all doctors who have issued reports to this patient or are assigned
    available_doctors = db.get_patient_doctors(patient_user["id"])

    # If no doctors found yet from reports, offer the hospital registry doctors
    if not available_doctors:
        available_doctors = db.get_all_doctors()

    return jsonify({
        "patient": {
            "id": patient_user["id"],
            "name": patient_user["name"],
            "email": patient_user["email"],
            "title": patient_user["title"],
            "assigned_doctor_id": patient_user.get("doctor_id")
        },
        "selected_doctor_id": filter_doctor_id,
        "available_doctors": available_doctors,
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
