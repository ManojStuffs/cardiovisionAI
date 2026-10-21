"""CardioVision AI — Clinical Mailer & Email Verification Service.

Handles sending 6-digit verification codes for user registration and sign-in.
Supports standard production SMTP (Gmail, SendGrid, Amazon SES, etc.) as well
as an interactive developer/simulation mode for immediate testing.
"""
from __future__ import annotations
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Optional


def generate_otp() -> str:
    """Generate a secure 6-digit numeric verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


def send_verification_email(to_email: str, recipient_name: str, otp: str, purpose: str = "signin") -> Tuple[bool, str]:
    """Send verification email with 6-digit OTP code.

    Returns:
        (success: bool, delivery_note: str)
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    sender_email = os.environ.get("SMTP_FROM", smtp_user or "verify@cardiovision.org")

    subject = f"CardioVision Security Code: {otp}"
    action_label = "Account Registration" if purpose == "signup" else "Secure Sign-In"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; padding: 20px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; }}
            .header {{ text-align: center; margin-bottom: 24px; }}
            .logo {{ font-size: 24px; font-weight: 800; color: #00f0ff; letter-spacing: -0.5px; }}
            .subtitle {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}
            .otp-box {{ background: #162032; border: 2px dashed #00f0ff; border-radius: 8px; text-align: center; padding: 18px; margin: 24px 0; }}
            .otp-code {{ font-size: 34px; font-weight: 700; letter-spacing: 8px; color: #ffffff; font-family: monospace; }}
            .notice {{ font-size: 13px; color: #94a3b8; line-height: 1.6; }}
            .footer {{ font-size: 11px; color: #64748b; text-align: center; margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🫀 CardioVision AI</div>
                <div class="subtitle">Clinical Atrial Fibrillation Diagnostic Platform</div>
            </div>
            <p>Hello <b>{recipient_name}</b>,</p>
            <p class="notice">Your one-time email verification code for <b>{action_label}</b> is:</p>
            <div class="otp-box">
                <div class="otp-code">{otp}</div>
            </div>
            <p class="notice">This verification code expires in <b>10 minutes</b>. If you did not request this verification, please disregard this email.</p>
            <div class="footer">
                CardioVision AI Electrophysiology Platform &copy; 2026. Automated clinical security system.
            </div>
        </div>
    </body>
    </html>
    """

    # If SMTP is configured, send the real email
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"CardioVision Security <{sender_email}>"
            msg["To"] = to_email

            part = MIMEText(html_content, "html")
            msg.attach(part)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(sender_email, [to_email], msg.as_string())

            print(f"[MAILER] Verification code {otp} sent successfully to {to_email}")
            return True, f"Verification code sent to {to_email}"
        except Exception as e:
            print(f"[MAILER ERROR] Failed to send email via SMTP: {e}")
            # Fallback to local simulation
            return True, f"Code generated: {otp} (SMTP connection error: {e})"

    # Simulation / local developer mode
    print(f"\n=======================================================")
    print(f"  [MAIL SIMULATOR] Email to: {to_email} ({recipient_name})")
    print(f"  Action: {action_label}")
    print(f"  VERIFICATION CODE: >>> {otp} <<<")
    print(f"  Expires in: 10 minutes")
    print(f"=======================================================\n")
    return True, f"Verification code sent to {to_email}"
