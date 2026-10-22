"""CardioVision AI — Clinical Database & Role-Based Security Engine.

Manages Users, Roles (Doctor with License Number, Patient assigned to Doctor),
Secure OTPs, Email Verification, and Clinical Diagnostic Reports using SQLite.
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
    """Initialize database tables and run schema migrations."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table with Doctor License & Patient Doctor Assignment
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,               -- 'doctor' or 'patient'
        title TEXT DEFAULT '',            -- Specialty or Age/MRN
        license_number TEXT DEFAULT '',   -- Mandatory for Doctor
        doctor_id INTEGER DEFAULT NULL,   -- For Patient: chosen Doctor
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Schema migration checks for existing tables
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [c["name"] for c in cursor.fetchall()]
    if "license_number" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN license_number TEXT DEFAULT ''")
    if "doctor_id" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN doctor_id INTEGER DEFAULT NULL")

    # Ensure any preexisting doctor records without a license get an official ID
    cursor.execute("UPDATE users SET license_number = 'MD-CARDIO-' || substr(hex(randomblob(3)), 1, 6) WHERE role = 'doctor' AND (license_number IS NULL OR license_number = '')")

    # OTP Verification Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        purpose TEXT NOT NULL,
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

    seed_default_data()


def seed_default_data():
    """Seed foundational doctor and patient records in SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Seed Doctor: Dr. Sarah Smith
    cursor.execute("SELECT id FROM users WHERE email = ?", ("dr.smith@cardiovision.org",))
    doctor = cursor.fetchone()
    if not doctor:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, license_number, is_verified)
        VALUES (?, ?, ?, 'doctor', 'Senior Electrophysiologist, Cardiology Dept.', 'MD-CARDIO-882914', 1)
        """, ("Dr. Sarah Smith", "dr.smith@cardiovision.org", pwd_hash))
        doctor_id = cursor.lastrowid
    else:
        doctor_id = doctor["id"]
        # Ensure license number is populated
        cursor.execute("UPDATE users SET license_number = 'MD-CARDIO-882914' WHERE id = ? AND (license_number IS NULL OR license_number = '')", (doctor_id,))

    # Seed Doctor 2: Dr. Robert Vance
    cursor.execute("SELECT id FROM users WHERE email = ?", ("dr.vance@cardiovision.org",))
    doctor2 = cursor.fetchone()
    if not doctor2:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, license_number, is_verified)
        VALUES (?, ?, ?, 'doctor', 'Associate Professor of Cardiology', 'MD-CARDIO-551029', 1)
        """, ("Dr. Robert Vance", "dr.vance@cardiovision.org", pwd_hash))
        doctor2_id = cursor.lastrowid
    else:
        doctor2_id = doctor2["id"]

    # Seed Patient 1: John Doe (Assigned to Dr. Sarah Smith)
    cursor.execute("SELECT id FROM users WHERE email = ?", ("john.doe@patient.org",))
    patient1 = cursor.fetchone()
    if not patient1:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, doctor_id, is_verified)
        VALUES (?, ?, ?, 'patient', 'Age: 58 | Patient ID: PT-9042', ?, 1)
        """, ("John Doe", "john.doe@patient.org", pwd_hash, doctor_id))
        patient1_id = cursor.lastrowid
    else:
        patient1_id = patient1["id"]
        cursor.execute("UPDATE users SET doctor_id = ? WHERE id = ? AND doctor_id IS NULL", (doctor_id, patient1_id))

    # Seed Patient 2: Emily Rose
    cursor.execute("SELECT id FROM users WHERE email = ?", ("emily.rose@patient.org",))
    patient2 = cursor.fetchone()
    if not patient2:
        pwd_hash = hash_password("Password123!")
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, doctor_id, is_verified)
        VALUES (?, ?, ?, 'patient', 'Age: 42 | Patient ID: PT-7183', ?, 1)
        """, ("Emily Rose", "emily.rose@patient.org", pwd_hash, doctor_id))
        patient2_id = cursor.lastrowid
    else:
        patient2_id = patient2["id"]

    # Seed Verified Sample Report for John Doe from Dr. Sarah Smith
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
            {"label": "AFIB", "title": "Atrial Fibrillation (AFib)", "score": 0.962, "percentage": 96.2, "urgency": "URGENT", "color": "#dc2626", "description": "Rapid, irregular atrial rhythm with absent P waves."},
            {"label": "NORM", "title": "Normal Sinus Rhythm", "score": 0.019, "percentage": 1.9, "urgency": "Routine", "color": "#16a34a", "description": "Regular physiological cardiac rhythm."},
            {"label": "STTC", "title": "ST/T-Wave Changes", "score": 0.010, "percentage": 1.0, "urgency": "Moderate", "color": "#d97706", "description": "Repolarization abnormalities."},
            {"label": "CD", "title": "Conduction Disturbance", "score": 0.006, "percentage": 0.6, "urgency": "Moderate", "color": "#ea580c", "description": "Conduction system delay."},
            {"label": "MI", "title": "Myocardial Infarction", "score": 0.003, "percentage": 0.3, "urgency": "URGENT", "color": "#b91c1c", "description": "Ischemic myocardial injury."}
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
            "ATRIAL FIBRILLATION DETECTED", 1, 96.2, "AFIB", 96.2, "Vision Transformer (ViT) & Arrhythmia Telemetry",
            "High RR variability (CV: 0.218) confirms irregularly irregular QRS timing with fibrillation waves.",
            "Initiate Apixaban 5mg BID for thromboembolism prophylaxis. Schedule outpatient 48h Holter monitoring and echocardiogram.",
            json.dumps(sample_telemetry),
            json.dumps(sample_preds),
            "/api/sample-image/afib_0.png"
        ))

    conn.commit()
    conn.close()


def create_user(
    name: str,
    email: str,
    password: str,
    role: str,
    title: str = "",
    license_number: str = "",
    doctor_id: Optional[int] = None,
    is_verified: bool = False
) -> Dict[str, Any]:
    """Create a new user with medical license or chosen doctor assignment."""
    email_clean = email.strip().lower()
    role_clean = "doctor" if role.lower() == "doctor" else "patient"
    pwd_hash = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, title, license_number, doctor_id, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name.strip(),
            email_clean,
            pwd_hash,
            role_clean,
            title.strip(),
            license_number.strip(),
            doctor_id,
            1 if is_verified else 0
        ))
        user_id = cursor.lastrowid
        conn.commit()
        return {
            "id": user_id,
            "name": name.strip(),
            "email": email_clean,
            "role": role_clean,
            "title": title.strip(),
            "license_number": license_number.strip(),
            "doctor_id": doctor_id,
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
    cursor.execute("""
    SELECT id, name, email, role, title, license_number, doctor_id, is_verified, created_at
    FROM users WHERE id = ?
    """, (user_id,))
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


def update_user_password(email: str, new_password: str) -> bool:
    """Update password hash for a user during password reset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    new_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_hash, email.strip().lower()))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def store_otp(email: str, otp: str, purpose: str = "signin", valid_seconds: int = 600):
    """Store verification OTP with expiry."""
    email_clean = email.strip().lower()
    expires_at = time.time() + valid_seconds
    conn = get_db_connection()
    cursor = conn.cursor()
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
        cursor.execute("DELETE FROM email_otps WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_all_doctors() -> List[Dict[str, Any]]:
    """Retrieve list of all registered doctors with license numbers."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, email, title, license_number, created_at FROM users
    WHERE role = 'doctor'
    ORDER BY name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_patients() -> List[Dict[str, Any]]:
    """Retrieve list of all registered patients."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, email, title, doctor_id, created_at FROM users
    WHERE role = 'patient'
    ORDER BY name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_patient_doctor(patient_id: int, doctor_id: int):
    """Update preferred/attending doctor for a patient."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET doctor_id = ? WHERE id = ?", (doctor_id, patient_id))
    conn.commit()
    conn.close()


def save_clinical_report(
    doctor_user: Dict[str, Any],
    patient_id: int,
    result_data: Dict[str, Any],
    notes: str,
    recommendation: str,
    image_url: str = ""
) -> Dict[str, Any]:
    """Save an official clinical report created by a doctor for a patient."""
    conn = get_db_connection()
    cursor = conn.cursor()

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

    doc_display_title = doctor_user.get("title", "Attending Cardiologist")
    if doctor_user.get("license_number"):
        doc_display_title += f" (Lic: {doctor_user['license_number']})"

    cursor.execute("""
    INSERT INTO reports (
        patient_id, patient_name, patient_email,
        doctor_id, doctor_name, doctor_title,
        verdict, is_afib, afib_percentage, top_condition, confidence, engine,
        doctor_notes, clinical_recommendation, telemetry_json, predictions_json, image_preview_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient["id"], patient["name"], patient["email"],
        doctor_user["id"], doctor_user["name"], doc_display_title,
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


def get_patient_reports(patient_id: int, doctor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve reports issued for a patient, optionally filtered by a specific doctor."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if doctor_id:
        cursor.execute("""
        SELECT * FROM reports
        WHERE patient_id = ? AND doctor_id = ?
        ORDER BY created_at DESC, id DESC
        """, (patient_id, doctor_id))
    else:
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


def get_patient_doctors(patient_id: int) -> List[Dict[str, Any]]:
    """Return list of distinct doctors who have either authored reports for this patient or are assigned."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT DISTINCT u.id, u.name, u.email, u.title, u.license_number
    FROM users u
    INNER JOIN reports r ON r.doctor_id = u.id
    WHERE r.patient_id = ?
    UNION
    SELECT u.id, u.name, u.email, u.title, u.license_number
    FROM users u
    INNER JOIN users p ON p.doctor_id = u.id
    WHERE p.id = ?
    ORDER BY name ASC
    """, (patient_id, patient_id))

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
