import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_suite():
    print("=" * 60)
    print("  CardioVision Clinical Verification & Security Test Suite")
    print("=" * 60)
    
    # 1. Test Web App Serving
    print("\n[1] Testing Root Web Application Delivery...")
    res = requests.get(f"{BASE_URL}/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "CardioVision" in res.text, "Index HTML missing CardioVision title"
    print("    [PASS] Index HTML delivered cleanly.")

    # 2. Test Doctor Registry
    print("\n[2] Testing Doctor Registry Endpoint (/api/doctors)...")
    res = requests.get(f"{BASE_URL}/api/doctors")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    docs = res.json()
    if isinstance(docs, dict) and "doctors" in docs:
        docs = docs["doctors"]
    print(f"    Found {len(docs)} registered doctors in clinical directory:")
    for d in docs:
        print(f"      - {d['name']} | Lic: {d.get('license_number')} | Email: {d['email']}")
        assert d.get('license_number'), f"Doctor {d['name']} missing license number!"
    print("    [PASS] Doctor registry verified.")

    # 3. Test Doctor Registration - License Enforcement
    print("\n[3] Testing Doctor Registration License Enforcement...")
    bad_doc_payload = {
        "email": "test.doc.nolicense@hospital.org",
        "password": "Password123!",
        "name": "Dr. Unlicensed",
        "role": "doctor"
        # license_number omitted intentionally
    }
    res = requests.post(f"{BASE_URL}/api/auth/register-request", json=bad_doc_payload)
    assert res.status_code == 400, f"Expected 400 for missing license, got {res.status_code}"
    assert "Medical License / Registration Number is required" in res.json().get("error", "")
    print(f"    [PASS] Correctly blocked unlicensed doctor registration: {res.json()['error']}")

    # 4. Test Doctor Registration with Valid License
    import time
    t_id = int(time.time())
    print("\n[4] Testing Doctor Registration with Valid License Number...")
    test_doc_email = f"dr.elena_{t_id}@cardiovision.org"
    good_doc_payload = {
        "email": test_doc_email,
        "password": "Password123!",
        "name": f"Dr. Elena Rostova {t_id}",
        "role": "doctor",
        "license_number": "MD-CARDIO-991204"
    }
    res = requests.post(f"{BASE_URL}/api/auth/register-request", json=good_doc_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    otp_code = res.json().get("dev_code")
    print(f"    [PASS] Registration OTP issued for Dr. Elena Rostova. OTP: {otp_code}")

    # Complete doctor registration
    verify_payload = {
        "email": test_doc_email,
        "code": otp_code,
        "password": "Password123!",
        "name": f"Dr. Elena Rostova {t_id}",
        "role": "doctor",
        "license_number": "MD-CARDIO-991204"
    }
    res = requests.post(f"{BASE_URL}/api/auth/verify-and-register", json=verify_payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}"
    new_doc_data = res.json()
    assert new_doc_data["user"]["license_number"] == "MD-CARDIO-991204"
    print(f"    [PASS] Dr. Elena Rostova registered successfully with license: {new_doc_data['user']['license_number']}")

    # 5. Test Doctor Sign-in Flow & Session
    print("\n[5] Testing Doctor Sign-In & Multi-Factor OTP Flow...")
    res = requests.post(f"{BASE_URL}/api/auth/login-request", json={
        "email": "dr.smith@cardiovision.org",
        "password": "Password123!"
    })
    assert res.status_code == 200, f"Login request failed: {res.text}"
    otp = res.json().get("dev_code")
    print(f"    [PASS] OTP generated for Dr. Sarah Smith: {otp}")

    res = requests.post(f"{BASE_URL}/api/auth/verify-and-login", json={
        "email": "dr.smith@cardiovision.org",
        "code": otp
    })
    assert res.status_code == 200, f"OTP verification failed: {res.text}"
    doc_session = res.json()
    doc_token = doc_session["token"]
    assert doc_session["user"]["role"] == "doctor"
    assert doc_session["user"]["license_number"] == "MD-CARDIO-882914"
    print(f"    [PASS] Authenticated Dr. Sarah Smith (Lic: {doc_session['user']['license_number']})")

    # 6. Test Patient Sign-in Flow & Session
    print("\n[6] Testing Patient Sign-In & OTP Flow...")
    res = requests.post(f"{BASE_URL}/api/auth/login-request", json={
        "email": "john.doe@patient.org",
        "password": "Password123!"
    })
    assert res.status_code == 200, f"Patient login request failed: {res.text}"
    p_otp = res.json().get("dev_code")

    res = requests.post(f"{BASE_URL}/api/auth/verify-and-login", json={
        "email": "john.doe@patient.org",
        "code": p_otp
    })
    assert res.status_code == 200, f"Patient OTP verification failed: {res.text}"
    pat_session = res.json()
    pat_token = pat_session["token"]
    assert pat_session["user"]["role"] == "patient"
    print(f"    [PASS] Authenticated Patient {pat_session['user']['name']} (ID: {pat_session['user']['id']})")

    # 7. Test Authorization: Patient FORBIDDEN from running /api/predict
    print("\n[7] Testing Strict Role Authorization: Patient blocked from /api/predict...")
    pat_headers = {"Authorization": f"Bearer {pat_token}"}
    res = requests.post(f"{BASE_URL}/api/predict", headers=pat_headers, files={"file": ("test.png", b"dummy")})
    assert res.status_code == 403, f"Expected 403 Forbidden for patient, got {res.status_code}"
    print(f"    [PASS] Patient blocked with 403 Forbidden: {res.json()['error']}")

    # 8. Test Patient Reports & Doctor Selection Filter
    print("\n[8] Testing Patient Reports with Doctor Filter...")
    res = requests.get(f"{BASE_URL}/api/patient/reports", headers=pat_headers)
    assert res.status_code == 200, f"Failed to get patient reports: {res.text}"
    report_data = res.json()
    reports = report_data.get("reports", [])
    avail_docs = report_data.get("available_doctors", [])
    print(f"    Found {len(reports)} diagnostic records for patient John Doe.")
    print(f"    Available attending doctors for filter: {[d['name'] for d in avail_docs]}")
    for r in reports:
        print(f"      - Record ID: {r['id']} | Verdict: {r.get('verdict') or r.get('prediction')} ({r['confidence']}%) | Attending: {r['doctor_name']} (Lic: {r.get('doctor_license') or r.get('doctor_title')})")

    # Filter specifically by Dr. Sarah Smith's ID
    if avail_docs:
        target_doc = avail_docs[0]
        res_filtered = requests.get(f"{BASE_URL}/api/patient/reports?doctor_id={target_doc['id']}", headers=pat_headers)
        assert res_filtered.status_code == 200
        filtered_reports = res_filtered.json().get("reports", [])
        print(f"    [PASS] Filter by Doctor '{target_doc['name']}' returned {len(filtered_reports)} certified records.")

    # 9. Test Unauthenticated Access Rejection
    print("\n[9] Testing Unauthorized Access Rejection without token...")
    res = requests.get(f"{BASE_URL}/api/patient/reports")
    assert res.status_code == 401, f"Expected 401 Unauthorized, got {res.status_code}"
    print("    [PASS] Unauthenticated access blocked with 401.")

    print("\n" + "=" * 60)
    print("  ALL 9 SECURITY & WORKFLOW TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_suite()
