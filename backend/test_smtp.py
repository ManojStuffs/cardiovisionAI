"""Diagnostic tool to test live SMTP email delivery directly from .env configuration."""
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.mailer import load_env_config, is_smtp_configured, send_verification_email, generate_otp

def main():
    print("=" * 65)
    print("  CardioVision AI — Live SMTP Verification Test")
    print("=" * 65)

    load_env_config()

    host = os.environ.get("SMTP_HOST", "")
    port = os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")

    print(f"SMTP Host: {host}")
    print(f"SMTP Port: {port}")
    print(f"SMTP User: {user}")
    print(f"SMTP Password: {'*' * len(password) if password else '[NOT SET]'}")
    print("-" * 65)

    if not is_smtp_configured():
        print("\n[ERROR] SMTP is not fully configured.")
        print("Please open '.env' in the project root and fill in:")
        print("  SMTP_USER=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-16-character-app-password")
        sys.exit(1)

    target_email = sys.argv[1].strip() if len(sys.argv) > 1 else user
    if not target_email:
        print("[ERROR] No destination email specified.")
        print("Usage: python backend/test_smtp.py <destination_email@domain.com>")
        sys.exit(1)

    test_otp = generate_otp()
    print(f"\nAttempting to dispatch test verification email to: {target_email} ...")
    success, msg, is_live = send_verification_email(
        to_email=target_email,
        recipient_name="CardioVision Tester",
        otp=test_otp,
        purpose="signup"
    )

    if success:
        print(f"\n[SUCCESS] Email successfully delivered to: {target_email}")
        print(f"Delivered OTP code: {test_otp}")
        print("Please check your email inbox (and spam/junk folder)!")
    else:
        print(f"\n[FAILED] Delivery failed: {msg}")

if __name__ == "__main__":
    main()
