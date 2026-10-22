import time
import requests

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("=" * 65)
    print("  CardioVision AI — Original Email Verification & Password Reset Tests")
    print("=" * 65)

    timestamp = int(time.time())

    # -------------------------------------------------------------
    # 1. Test Original Email Format Enforcement
    # -------------------------------------------------------------
    print("\n[1] Testing Original Email Format Validation & Rejection...")
    invalid_emails = [
        "notanemail",
        "doctor@",
        "@hospital.org",
        "test user@hospital.org",
        "missingdot@domain"
    ]
    for bad_email in invalid_emails:
        res = requests.post(f"{BASE_URL}/api/auth/register-request", json={
            "email": bad_email,
            "name": "Dr. Validation Test",
            "password": "Password123!",
            "role": "doctor",
            "license_number": "MD-CARDIO-112233"
        })
        assert res.status_code == 400, f"Expected 400 for '{bad_email}', got {res.status_code}"
        assert "valid, original email" in res.json().get("error", "").lower()
    print("    [PASS] Correctly rejected all malformed email formats.")

    # -------------------------------------------------------------
    # 2. Test Doctor Registration with Original Email Verification
    # -------------------------------------------------------------
    print("\n[2] Testing Doctor Registration with Original Email Verification...")
    doc_email = f"dr.sarah_verified_{timestamp}@hospital.org"
    doc_name = f"Dr. Sarah Verified {timestamp}"
    doc_license = f"MD-CARDIO-{timestamp % 1000000:06d}"
    doc_password = "SecureDocPass123!"

    # Step 1: Send Verification Code to Original Email
    res = requests.post(f"{BASE_URL}/api/auth/register-request", json={
        "email": doc_email,
        "name": doc_name,
        "password": doc_password,
        "role": "doctor",
        "license_number": doc_license,
        "title": "Clinical Cardiologist"
    })
    assert res.status_code == 200, f"Registration request failed: {res.text}"
    data = res.json()
    assert data["status"] == "otp_sent"
    assert data["email"] == doc_email
    otp_code = data.get("dev_code")
    assert otp_code and len(otp_code) == 6, f"Invalid OTP code: {otp_code}"
    print(f"    [PASS] 6-digit OTP code dispatched to {doc_email}: {otp_code}")

    # Step 2: Try invalid OTP first (should fail)
    bad_res = requests.post(f"{BASE_URL}/api/auth/verify-and-register", json={
        "email": doc_email,
        "code": "000000",
        "name": doc_name,
        "password": doc_password,
        "role": "doctor",
        "license_number": doc_license
    })
    assert bad_res.status_code == 400
    print(f"    [PASS] Correctly rejected invalid verification code.")

    # Step 3: Verify with real OTP and complete registration
    res = requests.post(f"{BASE_URL}/api/auth/verify-and-register", json={
        "email": doc_email,
        "code": otp_code,
        "name": doc_name,
        "password": doc_password,
        "role": "doctor",
        "license_number": doc_license,
        "title": "Clinical Cardiologist"
    })
    assert res.status_code == 201, f"Verify & register failed: {res.text}"
    doc_auth = res.json()
    assert doc_auth["user"]["email"] == doc_email
    assert doc_auth["user"]["license_number"] == doc_license
    assert doc_auth["token"]
    print(f"    [PASS] Doctor successfully verified original email and activated account.")

    # -------------------------------------------------------------
    # 3. Test Patient Registration with Original Email Verification
    # -------------------------------------------------------------
    print("\n[3] Testing Patient Registration with Original Email Verification...")
    # Fetch available doctor to link patient
    doc_res = requests.get(f"{BASE_URL}/api/doctors")
    assert doc_res.status_code == 200
    doctors = doc_res.json()
    target_doctor_id = doctors[0]["id"]

    patient_email = f"patient_verified_{timestamp}@gmail.com"
    patient_name = f"Robert Verified {timestamp}"
    patient_password = "SecurePatientPass123!"

    # Step 1: Send Verification Code to Original Email
    res = requests.post(f"{BASE_URL}/api/auth/register-request", json={
        "email": patient_email,
        "name": patient_name,
        "password": patient_password,
        "role": "patient",
        "doctor_id": target_doctor_id,
        "title": "Age: 52 | MRN-9912"
    })
    assert res.status_code == 200, f"Patient register request failed: {res.text}"
    p_data = res.json()
    p_otp = p_data.get("dev_code")
    assert p_otp and len(p_otp) == 6
    print(f"    [PASS] 6-digit OTP code dispatched to {patient_email}: {p_otp}")

    # Step 2: Verify OTP and create patient account
    res = requests.post(f"{BASE_URL}/api/auth/verify-and-register", json={
        "email": patient_email,
        "code": p_otp,
        "name": patient_name,
        "password": patient_password,
        "role": "patient",
        "doctor_id": target_doctor_id,
        "title": "Age: 52 | MRN-9912"
    })
    assert res.status_code == 201, f"Patient verify failed: {res.text}"
    pat_auth = res.json()
    assert pat_auth["user"]["email"] == patient_email
    assert pat_auth["user"]["doctor_id"] == target_doctor_id
    print(f"    [PASS] Patient successfully verified original email and activated account.")

    # -------------------------------------------------------------
    # 4. Test Resend Code Endpoint
    # -------------------------------------------------------------
    print("\n[4] Testing Resend Code Endpoint (/api/auth/resend-code)...")
    res = requests.post(f"{BASE_URL}/api/auth/resend-code", json={
        "email": doc_email,
        "purpose": "password_reset"
    })
    assert res.status_code == 200, f"Resend code failed: {res.text}"
    resent_data = res.json()
    assert resent_data["status"] == "code_resent"
    assert resent_data.get("dev_code")
    print(f"    [PASS] Resend code generated new security code: {resent_data['dev_code']}")

    # -------------------------------------------------------------
    # 5. Test Doctor Forgot Password & Reset via Email Verification
    # -------------------------------------------------------------
    print("\n[5] Testing Doctor Forgot Password Flow via Email Verification...")
    # Step 1: Request password reset
    res = requests.post(f"{BASE_URL}/api/auth/forgot-password-request", json={
        "email": doc_email
    })
    assert res.status_code == 200, f"Forgot password request failed: {res.text}"
    reset_otp = res.json().get("dev_code")
    assert reset_otp and len(reset_otp) == 6
    print(f"    [PASS] Password reset code dispatched to original email: {reset_otp}")

    # Step 2: Enter reset code & new password
    new_doc_password = "BrandNewDocPassword2026!"
    res = requests.post(f"{BASE_URL}/api/auth/reset-password", json={
        "email": doc_email,
        "code": reset_otp,
        "new_password": new_doc_password
    })
    assert res.status_code == 200, f"Password reset failed: {res.text}"
    reset_data = res.json()
    assert reset_data["status"] == "password_reset_success"
    print(f"    [PASS] Password updated successfully via email verification code.")

    # Step 3: Test direct sign-in with the NEW password and physician license
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": doc_email,
        "password": new_doc_password,
        "role": "doctor",
        "license_number": doc_license
    })
    assert login_res.status_code == 200, f"Login with new password failed: {login_res.text}"
    assert login_res.json()["user"]["email"] == doc_email
    print(f"    [PASS] Doctor successfully logged in with the NEW password.")

    # Step 4: Verify OLD password is now strictly rejected
    old_login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": doc_email,
        "password": doc_password,
        "role": "doctor",
        "license_number": doc_license
    })
    assert old_login_res.status_code == 401
    print(f"    [PASS] Old password correctly rejected after reset.")

    # -------------------------------------------------------------
    # 6. Test Patient Forgot Password & Reset via Email Verification
    # -------------------------------------------------------------
    print("\n[6] Testing Patient Forgot Password Flow via Email Verification...")
    # Step 1: Request password reset
    res = requests.post(f"{BASE_URL}/api/auth/forgot-password-request", json={
        "email": patient_email
    })
    assert res.status_code == 200, f"Patient forgot password failed: {res.text}"
    p_reset_otp = res.json().get("dev_code")
    assert p_reset_otp and len(p_reset_otp) == 6
    print(f"    [PASS] Patient password reset code dispatched: {p_reset_otp}")

    # Step 2: Change password with verification code
    new_patient_password = "BrandNewPatientPass2026!"
    res = requests.post(f"{BASE_URL}/api/auth/reset-password", json={
        "email": patient_email,
        "code": p_reset_otp,
        "new_password": new_patient_password
    })
    assert res.status_code == 200, f"Patient reset failed: {res.text}"
    print(f"    [PASS] Patient password updated successfully.")

    # Step 3: Direct sign-in with NEW password
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": patient_email,
        "password": new_patient_password,
        "role": "patient",
        "doctor_id": target_doctor_id
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["email"] == patient_email
    print(f"    [PASS] Patient successfully logged in with NEW password.")

    # -------------------------------------------------------------
    # 7. Test Non-existent Email Handling for Password Reset
    # -------------------------------------------------------------
    print("\n[7] Testing Non-Existent Email Handling...")
    fake_email = "nonexistent.user.2026@hospital.org"
    res = requests.post(f"{BASE_URL}/api/auth/forgot-password-request", json={
        "email": fake_email
    })
    assert res.status_code == 404
    assert "no registered account found" in res.json().get("error", "").lower()
    print(f"    [PASS] Handled unregistered email gracefully with 404.")

    print("\n" + "=" * 65)
    print("  ALL EMAIL VERIFICATION & PASSWORD RESET TESTS PASSED!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
