"""CardioVision AI — Clinical Database & Role-Based Security Engine.

Manages Users, Roles (Doctor, Patient), Secure OTPs, Email Verification,
and Clinical Patient Diagnostic Reports using SQLite.
"""
from __future__ import annotations
import os
import time
import json
import sqlite3
import hashlib
import secrets
import hmac
from pathlib import Path
from typing import Optional, Dict, Any, List

DB_PATH = Path(__file__).resolve().parent / "cardiovision.db"
SECRET_KEY = os.environ.get("SECRET_KEY", "cardiovision-super-secret-clinical-key-2026")


def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password with PBKDF2 HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${hashed}"


def check_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        salt, hashed = stored_hash.split("$", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(hashed, expected)
    except Exception:
        return False


def generate_auth_token(user: Dict[str, Any]) -> str:
    """Generate a tamper-proof session token."""
    payload = {
        "uid": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": int(time.time()) + 86400 * 7  # 7 days
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
    # base64-like hex encoding
    raw = f"{payload_str.encode('utf-8').hex()}.{signature}"
    return raw


def verify_auth_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify the auth token."""
    if not token or "." not in token:
        return None
    try:
        hex_data, signature = token.split(".", 1)
        payload_str = bytes.fromhex(hex_data).decode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(payload_str)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def init_db():
    """Initialize database tables and seed sample accounts."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,          -- 'doctor' or 'patient'
        title TEXT DEFAULT '',       -- e.g. 'Cardiologist' or 'Patient Age: 58'
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # OTP Verification Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        purpose TEXT NOT NULL,       -- 'signup' or 'signin'
        expires_at REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Clinical Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        patient_name TEXT NOT NULL,
        patient_email TEXT NOT NULL,
        doctor_id INTEGER NOT NULL,
        doctor_name TEXT NOT NULL,
        doctor_title TEXT DEFAULT 'Cardiologist',
        verdict TEXT NOT NULL,
        is_afib INTEGER NOT NULL,
        afib_percentage REAL NOT NULL,
        top_condition TEXT NOT NULL,
        confidence REAL NOT NULL,
        engine TEXT DEFAULT 'Vision Transformer (ViT)',
        doctor_notes TEXT DEFAULT '',
        clinical_recommendation TEXT DEFAULT '',
        telemetry_json TEXT DEFAULT '{}',
        predictions_json TEXT DEFAULT '[]',
        image_preview_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES users (id),
        FOREIGN KEY (doctor_id) REFERENCES users (id)
    )
    """)

    conn.commit()
    conn.close()

    # Seed default doctor, patient, and verified sample report
    seed_default_data()


def seed_default_data():
    """Seed test accounts so doctors and patients can be immediately demonstrated."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Seed Doctor: Dr. Sarah Smith
    cursor.execute("SELECT id FROM users WHERE email = ?", ("dr.smith@cardiovision.org",))
    doctor = cursor.fetchone()
    if not doctor:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, is_verified)
        VALUES (?, ?, ?, 'doctor', 'Senior Electrophysiologist, Cardiology Dept.', 1)
        """, ("Dr. Sarah Smith", "dr.smith@cardiovision.org", pwd_hash))
        doctor_id = cursor.lastrowid
    else:
        doctor_id = doctor["id"]

    # Seed Patient 1: John Doe
    cursor.execute("SELECT id FROM users WHERE email = ?", ("john.doe@patient.org",))
    patient1 = cursor.fetchone()
    if not patient1:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, is_verified)
        VALUES (?, ?, ?, 'patient', 'Age: 58 | ID: PT-9042', 1)
        """, ("John Doe", "john.doe@patient.org", pwd_hash))
        patient1_id = cursor.lastrowid
    else:
        patient1_id = patient1["id"]

    # Seed Patient 2: Emily Rose
    cursor.execute("SELECT id FROM users WHERE email = ?", ("emily.rose@patient.org",))
    patient2 = cursor.fetchone()
    if not patient2:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, is_verified)
        VALUES (?, ?, ?, 'patient', 'Age: 42 | ID: PT-7183', 1)
        """, ("Emily Rose", "emily.rose@patient.org", pwd_hash))
        patient2_id = cursor.lastrowid
    else:
        patient2_id = patient2["id"]

    # Seed Initial Verified Report for John Doe if none exists
    cursor.execute("SELECT id FROM reports WHERE patient_id = ?", (patient1_id,))
    if not cursor.fetchone():
        sample_telemetry = {
            "n_beats": 14,
            "rr_cv": 0.218,
            "sampling_rate": 250.0,
            "signal_duration_sec": 10.0,
            "waveform_preview": {
                "times": [round(i * 0.05, 2) for i in range(200)],
                "values": [round(int(hashlib.md5(str(i).encode()).hexdigest()[:2], 16) / 255.0 - 0.5, 3) for i in range(200)],
                "peak_indices": [0.65, 1.42, 2.15, 2.95, 3.82, 4.51, 5.34, 6.12, 6.95, 7.82, 8.65, 9.42]
            }
        }
        sample_preds = [
            {"label": "AFIB", "title": "Atrial Fibrillation (AFib)", "score": 0.884, "percentage": 88.4, "urgency": "URGENT", "color": "#ff3366", "description": "Rapid, irregular atrial rhythm with absent P waves."},
            {"label": "NORM", "title": "Normal Sinus Rhythm", "score": 0.062, "percentage": 6.2, "urgency": "Routine", "color": "#00e676", "description": "Regular physiological cardiac rhythm."},
            {"label": "STTC", "title": "ST/T-Wave Changes", "score": 0.034, "percentage": 3.4, "urgency": "Moderate", "color": "#ffab00", "description": "Repolarization abnormalities."},
            {"label": "CD", "title": "Conduction Disturbance", "score": 0.012, "percentage": 1.2, "urgency": "Moderate", "color": "#ff9100", "description": "Conduction system delay."},
            {"label": "MI", "title": "Myocardial Infarction", "score": 0.008, "percentage": 0.8, "urgency": "URGENT", "color": "#ff1744", "description": "Ischemic myocardial injury."}
        ]
        cursor.execute("""
        INSERT INTO reports (
            patient_id, patient_name, patient_email,
            doctor_id, doctor_name, doctor_title,
            verdict, is_afib, afib_percentage, top_condition, confidence, engine,
            doctor_notes, clinical_recommendation, telemetry_json, predictions_json, image_preview_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient1_id, "John Doe", "john.doe@patient.org",
            doctor_id, "Dr. Sarah Smith", "Senior Electrophysiologist, Cardiology Dept.",
            "ATRIAL FIBRILLATION DETECTED", 1, 88.4, "AFIB", 88.4, "CardioVision DeepNet ViT",
            "High RR variability (CV: 0.218) confirms irregularly irregular QRS timing with fibrillation waves.",
            "Initiate Apixaban 5mg BID for thromboembolism prophylaxis. Schedule outpatient 48h Holter monitoring and echocardiogram.",
            json.dumps(sample_telemetry),
            json.dumps(sample_preds),
            "/api/sample-image/afib_0.png"
        ))

    conn.commit()
    conn.close()


def create_user(name: str, email: str, password: str, role: str, title: str = "", is_verified: bool = False) -> Dict[str, Any]:
    """Create a new user in the database."""
    email_clean = email.strip().lower()
    role_clean = "doctor" if role.lower() == "doctor" else "patient"
    pwd_hash = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, is_verified)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (name.strip(), email_clean, pwd_hash, role_clean, title.strip(), 1 if is_verified else 0))
        user_id = cursor.lastrowid
        conn.commit()
        return {
            "id": user_id,
            "name": name.strip(),
            "email": email_clean,
            "role": role_clean,
            "title": title.strip(),
            "is_verified": bool(is_verified)
        }
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary by email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary by user id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, title, is_verified, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def set_user_verified(email: str):
    """Mark user email as verified."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email.strip().lower(),))
    conn.commit()
    conn.close()


def store_otp(email: str, otp: str, purpose: str = "signin", valid_seconds: int = 600):
    """Store verification OTP with expiry."""
    email_clean = email.strip().lower()
    expires_at = time.time() + valid_seconds
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete old OTPs for this email and purpose
    cursor.execute("DELETE FROM email_otps WHERE email = ? AND purpose = ?", (email_clean, purpose))
    cursor.execute("""
    INSERT INTO email_otps (email, otp, purpose, expires_at)
    VALUES (?, ?, ?, ?)
    """, (email_clean, otp.strip(), purpose, expires_at))
    conn.commit()
    conn.close()


def verify_otp(email: str, otp: str, purpose: str = "signin") -> bool:
    """Check if provided OTP is valid and within expiry window."""
    email_clean = email.strip().lower()
    now = time.time()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, expires_at FROM email_otps
    WHERE email = ? AND otp = ? AND purpose = ?
    ORDER BY id DESC LIMIT 1
    """, (email_clean, otp.strip(), purpose))
    row = cursor.fetchone()
    if row and row["expires_at"] >= now:
        # OTP is valid, remove it
        cursor.execute("DELETE FROM email_otps WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_all_patients() -> List[Dict[str, Any]]:
    """Retrieve list of all registered patients."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, email, title, created_at FROM users
    WHERE role = 'patient'
    ORDER BY name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_clinical_report(doctor_user: Dict[str, Any], patient_id: int, result_data: Dict[str, Any], notes: str, recommendation: str, image_url: str = "") -> Dict[str, Any]:
    """Save an official clinical report created by a doctor for a patient."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get patient details
    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        raise ValueError("Selected patient does not exist.")

    telemetry = result_data.get("telemetry", {})
    predictions = result_data.get("predictions", [])
    is_afib = 1 if result_data.get("is_afib") else 0
    afib_pct = float(result_data.get("afib_percentage", 0.0))
    verdict = result_data.get("verdict", "ATRIAL FIBRILLATION EVALUATED")
    top_cond = result_data.get("top_condition", "NORM")
    confidence = float(result_data.get("confidence", 0.0))
    engine = result_data.get("engine", "CardioVision DeepNet ViT")

    cursor.execute("""
    INSERT INTO reports (
        patient_id, patient_name, patient_email,
        doctor_id, doctor_name, doctor_title,
        verdict, is_afib, afib_percentage, top_condition, confidence, engine,
        doctor_notes, clinical_recommendation, telemetry_json, predictions_json, image_preview_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient["id"], patient["name"], patient["email"],
        doctor_user["id"], doctor_user["name"], doctor_user.get("title", "Cardiologist"),
        verdict, is_afib, afib_pct, top_cond, confidence, engine,
        notes.strip(), recommendation.strip(),
        json.dumps(telemetry), json.dumps(predictions), image_url
    ))
    report_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    new_report = dict(cursor.fetchone())
    conn.close()

    new_report["telemetry"] = telemetry
    new_report["predictions"] = predictions
    return new_report


def get_patient_reports(patient_id: int) -> List[Dict[str, Any]]:
    """Retrieve all reports issued for a specific patient, ordered by date desc."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM reports
    WHERE patient_id = ?
    ORDER BY created_at DESC, id DESC
    """, (patient_id,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["telemetry"] = json.loads(item.get("telemetry_json", "{}"))
        except Exception:
            item["telemetry"] = {}
        try:
            item["predictions"] = json.loads(item.get("predictions_json", "[]"))
        except Exception:
            item["predictions"] = []
        results.append(item)
    return results


def get_doctor_reports(doctor_id: int) -> List[Dict[str, Any]]:
    """Retrieve all reports generated by a specific doctor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM reports
    WHERE doctor_id = ?
    ORDER BY created_at DESC, id DESC
    """, (doctor_id,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["telemetry"] = json.loads(item.get("telemetry_json", "{}"))
        except Exception:
            item["telemetry"] = {}
        try:
            item["predictions"] = json.loads(item.get("predictions_json", "[]"))
        except Exception:
            item["predictions"] = []
        results.append(item)
    return results
