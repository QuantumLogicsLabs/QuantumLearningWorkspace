import os
import smtplib
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path, override=True)
logger = logging.getLogger("uvicorn")


def _send_smtp_sync(to_email: str, otp_code: str, host: str, port: int, user: str, password: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your StudyMind AI Verification Code: {otp_code}"
        msg["From"] = f"StudyMind AI <{user}>"
        msg["To"] = to_email

        text = (
            f"Welcome to StudyMind AI!\n\n"
            f"Your 6-digit verification code is: {otp_code}\n\n"
            f"This code will expire in 10 minutes. If you did not request this, please ignore this email."
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
    .card {{ max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    .logo {{ font-size: 24px; font-weight: 800; color: #6366f1; }}
    .title {{ font-size: 20px; font-weight: 700; color: #1e293b; margin-top: 8px; }}
    .desc {{ font-size: 14px; color: #64748b; line-height: 1.5; }}
    .otp-box {{ background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 8px; padding: 16px; text-align: center; margin: 24px 0; }}
    .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #4f46e5; font-family: 'Courier New', monospace; }}
    .footer {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">StudyMind AI</div>
      <div class="title">Verify Your Email</div>
    </div>
    <p class="desc">Thank you for signing up for StudyMind AI. Please use the following 6-digit verification code to complete your registration:</p>
    <div class="otp-box">
      <div class="otp-code">{otp_code}</div>
    </div>
    <p class="desc" style="font-size: 13px; text-align: center;">This code will expire in <strong>10 minutes</strong>.<br>If you didn't create an account, you can safely ignore this email.</p>
    <div class="footer">&copy; StudyMind AI Learning Platform. All rights reserved.</div>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to_email], msg.as_string())

        logger.info(f"Successfully delivered OTP email to {to_email}")
        return True
    except Exception as e:
        logger.warning(f"Failed to send email via SMTP ({host}:{port}): {e}")
        return False


async def send_otp_email(to_email: str, otp_code: str) -> bool:
    load_dotenv(_env_path, override=True)
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()

    if not user or not password:
        # Local development mode without SMTP credentials:
        # Print OTP to console so developers can test locally without real email.
        print("\n" + "=" * 55, flush=True)
        print("[StudyMind AI OTP Verification - DEV MODE (No SMTP)]", flush=True)
        print(f"   Recipient: {to_email}", flush=True)
        print(f"   Code:      >>> {otp_code} <<< (Valid for 10 minutes)", flush=True)
        print("=" * 55 + "\n", flush=True)
        logger.info(f"[EMAIL OTP DEV] Code for {to_email} is {otp_code}")
        return True

    # Real SMTP is active: Never leak the plaintext OTP code into server logs!
    logger.info(f"[EMAIL OTP] Verification email dispatched to {to_email}")
    print(f"[EMAIL OTP] Verification email successfully sent to {to_email}", flush=True)

    return await asyncio.to_thread(_send_smtp_sync, to_email, otp_code, host, port, user, password)

