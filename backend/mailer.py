"""CardioVision AI — Clinical Mailer & Email Verification Service.

Handles sending 6-digit verification codes for user registration, sign-in,
and password reset verification to original user email addresses.
Supports standard production SMTP (Gmail, SendGrid, Amazon SES, etc.) as well
as an interactive developer/simulation mode for immediate testing.
"""
from __future__ import annotations
import os
import secrets
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

# Load .env file if present in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = PROJECT_ROOT / ".env"


def load_env_config():
    """Dynamically reload .env configuration so credential updates take effect immediately."""
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except Exception as e:
            print(f"[MAILER] Notice loading .env: {e}")


load_env_config()


def generate_otp() -> str:
    """Generate a secure 6-digit numeric verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


def is_smtp_configured() -> bool:
    """Check if SMTP credentials are fully provided in environment."""
    load_env_config()
    host = (os.environ.get("SMTP_HOST") or "").strip()
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASSWORD") or "").strip()
    return bool(host and user and password)


def send_verification_email(to_email: str, recipient_name: str, otp: str, purpose: str = "signin") -> Tuple[bool, str, bool]:
    """Send verification email with 6-digit OTP code to the user's original email address.

    Args:
        to_email: Destination email address
        recipient_name: User display name
        otp: 6-digit numeric security code
        purpose: 'signup' | 'password_reset' | 'signin'

    Returns:
        (success: bool, delivery_message: str, is_live_smtp: bool)
    """
    load_env_config()
    clean_email = to_email.strip().lower()
    smtp_host = (os.environ.get("SMTP_HOST") or "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = (os.environ.get("SMTP_USER") or "").strip()
    smtp_pass = (os.environ.get("SMTP_PASSWORD") or "").strip()
    # Strip spaces from Google App Passwords (e.g. 'abcd efgh ijkl mnop' -> 'abcdefghijklmnop')
    if "gmail.com" in smtp_host.lower():
        smtp_pass = smtp_pass.replace(" ", "")
    sender_email = (os.environ.get("SMTP_FROM") or "").strip() or smtp_user or "verify@cardiovision.org"

    if purpose == "password_reset":
        subject = f"CardioVision AI — Password Reset Verification Code: {otp}"
        action_title = "Password Reset Request"
        action_desc = "We received a request to reset your password for the CardioVision Healthcare System. Use the 6-digit verification code below to authorize your password change."
    elif purpose == "signup":
        subject = f"CardioVision AI — Account Verification Code: {otp}"
        action_title = "Account Registration Verification"
        action_desc = "Thank you for registering with CardioVision Healthcare System. Please verify your original email address using the 6-digit verification code below to complete account activation."
    else:
        subject = f"CardioVision AI — Security Verification Code: {otp}"
        action_title = "Workstation Sign-In Verification"
        action_desc = "A sign-in attempt was initiated for your CardioVision clinical account. Please verify your identity using the one-time security code below."

    # Professional Hospital-Grade HTML Email Template
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                color: #0f172a;
                line-height: 1.5;
            }}
            .wrapper {{
                width: 100%;
                background-color: #f8fafc;
                padding: 32px 16px;
            }}
            .container {{
                max-width: 540px;
                margin: 0 auto;
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 32px;
                box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.05);
            }}
            .brand-badge {{
                display: inline-block;
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                color: #1e40af;
                padding: 4px 12px;
                border-radius: 9999px;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.02em;
                margin-bottom: 12px;
            }}
            .header-title {{
                font-size: 20px;
                font-weight: 700;
                color: #0f172a;
                margin: 0 0 4px 0;
            }}
            .header-sub {{
                font-size: 13px;
                color: #64748b;
                margin: 0 0 24px 0;
            }}
            .recipient-greeting {{
                font-size: 15px;
                font-weight: 600;
                color: #1e293b;
                margin: 0 0 12px 0;
            }}
            .instruction-text {{
                font-size: 14px;
                color: #334155;
                margin: 0 0 20px 0;
            }}
            .code-card {{
                background-color: #f8fafc;
                border: 2px dashed #cbd5e1;
                border-radius: 8px;
                text-align: center;
                padding: 24px 16px;
                margin: 20px 0;
            }}
            .code-label {{
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #64748b;
                margin-bottom: 8px;
            }}
            .code-digits {{
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                font-size: 36px;
                font-weight: 800;
                letter-spacing: 8px;
                color: #1e40af;
            }}
            .security-notice {{
                font-size: 12px;
                color: #64748b;
                background-color: #f1f5f9;
                border-left: 3px solid #1e40af;
                padding: 10px 14px;
                border-radius: 0 4px 4px 0;
                margin: 20px 0;
            }}
            .footer {{
                font-size: 11px;
                color: #94a3b8;
                border-top: 1px solid #e2e8f0;
                padding-top: 16px;
                margin-top: 24px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="brand-badge">CardioVision Healthcare System</div>
                <h1 class="header-title">{action_title}</h1>
                <p class="header-sub">Clinical Cardiology & Arrhythmia Diagnostic Platform</p>

                <p class="recipient-greeting">Hello {recipient_name or 'User'},</p>
                <p class="instruction-text">{action_desc}</p>

                <div class="code-card">
                    <div class="code-label">6-Digit Verification Code</div>
                    <div class="code-digits">{otp}</div>
                </div>

                <div class="security-notice">
                    <strong>Security Advisory:</strong> This code is single-use and will expire in <strong>10 minutes</strong>. Never share this security code with anyone. CardioVision staff will never ask for your code.
                </div>

                <div class="footer">
                    CardioVision AI Healthcare System &bull; HL7 & HIPAA Compliant Clinical Engine &bull; Automated Security Service
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # 1. Attempt sending real email via SMTP if credentials are configured
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"CardioVision AI <{sender_email}>"
            msg["To"] = clean_email
            msg["Reply-To"] = sender_email

            plain_text = (
                f"CardioVision AI Healthcare System\n"
                f"{action_title}\n\n"
                f"Hello {recipient_name or 'User'},\n\n"
                f"{action_desc}\n\n"
                f"YOUR 6-DIGIT VERIFICATION CODE: {otp}\n\n"
                f"This single-use security code expires in 10 minutes.\n"
                f"Enter this code on the website to complete your verification.\n\n"
                f"CardioVision AI Healthcare System — HIPAA & HL7 Compliant Engine"
            )
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if smtp_port == 465:
                # SSL Direct Connection (e.g., Gmail SSL port 465)
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(sender_email, [clean_email], msg.as_string())
            else:
                # STARTTLS Connection (e.g., Gmail / SendGrid / Brevo port 587)
                with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(sender_email, [clean_email], msg.as_string())

            print(f"[MAILER SUCCESS] Original email verification code delivered via SMTP to: {clean_email}")
            return True, f"A 6-digit verification code has been dispatched to {clean_email}. Please check your inbox and spam folder.", True
        except smtplib.SMTPAuthenticationError as e:
            err_msg = (
                f"SMTP authentication failed for user '{smtp_user}'. "
                "If using Gmail, please ensure you use a 16-character Google App Password (not your normal Google account password). "
                "Visit https://myaccount.google.com/apppasswords to create one."
            )
            print(f"[MAILER AUTH ERROR] {err_msg} (Details: {e})")
            return False, err_msg, False
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
            err_msg = f"Could not connect to SMTP server '{smtp_host}:{smtp_port}'. Please check your internet connection and SMTP_HOST/SMTP_PORT settings."
            print(f"[MAILER NETWORK ERROR] {err_msg} (Details: {e})")
            return False, err_msg, False
        except Exception as e:
            err_msg = f"Failed to dispatch verification email to {clean_email} via SMTP: {e}"
            print(f"[MAILER SMTP ERROR] {err_msg}")
            return False, err_msg, False

    # 2. If SMTP is not configured in .env
    err_msg = (
        "Email verification delivery failed: SMTP is not configured in .env. "
        "To receive verification codes directly in your original email inbox (e.g. Gmail), "
        "please set your SMTP credentials (SMTP_USER and Google App Password) in your .env file."
    )
    print(f"[MAILER WARNING] {err_msg}")
    return False, err_msg, False
