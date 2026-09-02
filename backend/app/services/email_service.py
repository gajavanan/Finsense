"""
FinSense Email Service
Used for:
1. Forgot Password / Password Reset links
2. Security notifications (e.g. login alerts)
"""
import logging
import smtplib
import ssl
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

def _resend_configured() -> bool:
    """Check if Resend API key is present and valid."""
    key = getattr(settings, "RESEND_API_KEY", "") or ""
    return bool(key.strip() and key.strip() != "dummy")

def _smtp_configured() -> bool:
    """Check if SMTP credentials are fully provided."""
    return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)

def _email_from() -> str:
    """Return the sender email address."""
    if _get_active_provider() == "resend":
        return settings.EMAIL_FROM or "FinSense <onboarding@resend.dev>"
    return settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or settings.EMAIL_FROM or "FinSense <onboarding@resend.dev>"

def _email_provider() -> str:
    return (getattr(settings, "EMAIL_PROVIDER", "auto") or "auto").lower().strip()

def _get_active_provider() -> str:
    """
    Determine active provider:
    1. If EMAIL_PROVIDER is explicitly set to 'resend' or 'smtp', honor it.
    2. In production (APP_ENV=production), ALWAYS prefer Resend because Render Free tier
       blocks outbound SMTP ports 25, 465, and 587.
    3. In development, prefer Resend if RESEND_API_KEY is configured; otherwise fallback to SMTP.
    """
    provider = _email_provider()
    is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")

    if provider == "resend":
        return "resend"
    if provider == "smtp":
        if is_prod and not _resend_configured():
            logger.warning(
                "[EMAIL] Warning: SMTP selected in production on Render. "
                "Render Free tier blocks outbound SMTP ports (25, 465, 587). "
                "Configure RESEND_API_KEY to ensure delivery."
            )
        return "smtp"

    # auto mode:
    if _resend_configured():
        return "resend"
    if not is_prod and _smtp_configured():
        return "smtp"
    # Default to resend for cloud/container environments
    return "resend"

def _mask_secret(msg: str) -> str:
    """Sanitize error messages to remove any potential credential leaks."""
    if not msg:
        return ""
    clean = msg
    if getattr(settings, "SMTP_PASSWORD", None) and settings.SMTP_PASSWORD in clean:
        clean = clean.replace(settings.SMTP_PASSWORD, "***")
    if getattr(settings, "RESEND_API_KEY", None) and settings.RESEND_API_KEY in clean:
        clean = clean.replace(settings.RESEND_API_KEY, "***")
    return clean

def _log_safe(action: str, recipient: str, success: bool, error: str = ""):
    # NEVER log password, token, JWT or API keys
    safe_error = _mask_secret(error)
    status = "successful" if success else f"failed: {safe_error}"
    provider = _get_active_provider().upper()
    logger.info(f"[EMAIL] {action} | Recipient: {recipient} | Provider: {provider} | Status: {status}")
    print(f"[EMAIL] {action} | Recipient: {recipient} | Provider: {provider} | Success: {success} {safe_error}")

async def _send_resend(to_email: str, subject: str, html: str) -> dict:
    """Send transactional email via Resend HTTPS API (port 443 - works on Render Free)."""
    if not _resend_configured():
        err = "RESEND_API_KEY is not configured in environment variables."
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}

    from_addr = _email_from()
    api_key = settings.RESEND_API_KEY.strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    try:
        print(f"[EMAIL RESEND] Sending via Resend HTTPS API to {to_email} (from: {from_addr})")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
            try:
                data = resp.json()
            except Exception:
                data = {}

            if resp.status_code >= 400:
                raw_msg = data.get("message") or f"Resend API error (HTTP {resp.status_code})"
                err = _mask_secret(str(raw_msg))
                _log_safe(subject, to_email, False, err)
                return {"ok": False, "error": err}

            email_id = data.get("id", "ok")
            _log_safe(subject, to_email, True)
            return {"ok": True, "id": email_id}
    except Exception as e:
        # Fallback to official resend SDK if installed
        try:
            import resend
            resend.api_key = api_key
            r = resend.Emails.send(payload)
            email_id = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else "ok")
            _log_safe(subject, to_email, True)
            return {"ok": True, "id": email_id}
        except Exception as sdk_err:
            err = _mask_secret(f"{type(e).__name__}: {str(e)}")
            _log_safe(subject, to_email, False, err)
            return {"ok": False, "error": err}

def _send_smtp(to_email: str, subject: str, html: str, text_fallback: str = "") -> dict:
    """Send via SMTP (port 587 / TLS). Note: Blocked on Render Free web services."""
    if not _smtp_configured():
        err = "SMTP not configured - set SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD"
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}

    from_addr = _email_from()
    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject

    if not text_fallback:
        text_fallback = re.sub(r"<[^>]+>", "", html)
    msg.attach(MIMEText(text_fallback, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        print(f"[EMAIL SMTP] Connecting to {settings.SMTP_HOST}:{settings.SMTP_PORT} TLS={settings.SMTP_USE_TLS}")
        if settings.SMTP_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15, context=ssl.create_default_context()) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(from_addr, [to_email], msg.as_string())
        _log_safe(subject, to_email, True)
        return {"ok": True}
    except smtplib.SMTPAuthenticationError as e:
        err = f"SMTP authentication failed: {e.smtp_code}"
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}
    except OSError as e:
        # Catch Errno 101 Network unreachable (Render Free tier blocks port 587)
        err = f"SMTP network unreachable (ports blocked by cloud host): {e}"
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}
    except Exception as e:
        err = _mask_secret(f"SMTP error ({type(e).__name__}): {e}")
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}

async def _send_email(to_email: str, subject: str, html: str, text_fallback: str = "") -> dict:
    """Central email dispatcher respecting active provider and fallbacks."""
    provider = _get_active_provider()
    if provider == "resend":
        res = await _send_resend(to_email, subject, html)
        if res.get("ok"):
            return res
        # If Resend failed and SMTP is configured locally, try SMTP fallback
        if _smtp_configured() and getattr(settings, "APP_ENV", "development").lower() != "production":
            print(f"[EMAIL] Resend failed ({res.get('error')}); falling back to local SMTP...")
            return _send_smtp(to_email, subject, html, text_fallback)
        return res
    elif provider == "smtp":
        res = _send_smtp(to_email, subject, html, text_fallback)
        if res.get("ok"):
            return res
        # If SMTP failed (e.g. network unreachable) and Resend is configured, try Resend
        if _resend_configured():
            print(f"[EMAIL] SMTP failed ({res.get('error')}); attempting Resend HTTPS fallback...")
            return await _send_resend(to_email, subject, html)
        return res
    else:
        err = "No active email provider configured. Please configure RESEND_API_KEY in Render."
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}

# -----------------------------------------------------------------------------
# Public Service API
# -----------------------------------------------------------------------------

async def send_verification_email(email: str, name: str, token: str):
    """Send verification email containing FRONTEND_URL verification link."""
    frontend_url = settings.FRONTEND_URL.strip().rstrip("/")
    link = f"{frontend_url}/verify-email?token={token}"
    subject = "Verify your FinSense account"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden">
      <div style="background:linear-gradient(135deg,#0ea5e9,#7c3aed);padding:24px;text-align:center;color:white">
        <div style="background:white;color:#0ea5e9;width:40px;height:40px;border-radius:10px;display:inline-grid;place-items:center;font-weight:bold;margin:0 auto">●</div>
        <h1 style="margin:12px 0 0;font-size:22px">FinSense</h1>
        <p style="opacity:0.9;margin:4px 0 0;font-size:13px">AI-Powered Personal Finance</p>
      </div>
      <div style="padding:28px">
        <p style="font-size:15px;color:#334155">Hello {name},</p>
        <p style="font-size:14px;color:#475569;line-height:1.6">Welcome to FinSense.</p>
        <p style="font-size:14px;color:#475569;line-height:1.6">Please verify your email address by clicking the button below. This link expires in <strong>24 hours</strong>.</p>
        <div style="text-align:center;margin:28px 0">
          <a href="{link}" style="background:#0ea5e9;color:white;padding:12px 28px;border-radius:10px;text-decoration:none;font-weight:600;display:inline-block">Verify Email</a>
        </div>
        <p style="font-size:12px;color:#64748b">Or copy this link: <a href="{link}" style="color:#0ea5e9;word-break:break-all">{link}</a></p>
        <p style="font-size:12px;color:#64748b;margin-top:20px">If you did not create this account, you can safely ignore this email.</p>
        <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0"/>
        <p style="font-size:11px;color:#94a3b8">FinSense Security Team • This is an automated message, please do not reply.</p>
      </div>
    </div>
    """

    res = await _send_email(email, subject, html)
    if not res.get("ok"):
        raise RuntimeError(res.get("error", "Failed to deliver verification email"))
    return res

async def send_password_reset_email(email: str, name: str, token: str):
    """Send password reset link."""
    frontend_url = settings.FRONTEND_URL.strip().rstrip("/")
    link = f"{frontend_url}/reset-password?token={token}"
    subject = "FinSense – Password Reset Request"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden">
      <div style="background:linear-gradient(135deg,#0ea5e9,#7c3aed);padding:24px;text-align:center;color:white">
        <h1 style="margin:12px 0 0;font-size:22px">FinSense</h1>
        <p style="opacity:0.9;margin:4px 0 0;font-size:13px">Password Reset Request</p>
      </div>
      <div style="padding:28px">
        <p style="font-size:15px;color:#334155">Hello {name},</p>
        <p style="font-size:14px;color:#475569;line-height:1.6">We received a request to reset your FinSense account password. This link expires in <strong>1 hour</strong>.</p>
        <div style="text-align:center;margin:28px 0">
          <a href="{link}" style="background:#0ea5e9;color:white;padding:12px 28px;border-radius:10px;text-decoration:none;font-weight:600;display:inline-block">Reset Password</a>
        </div>
        <p style="font-size:12px;color:#64748b">Or copy this link: <a href="{link}" style="color:#0ea5e9;word-break:break-all">{link}</a></p>
        <p style="font-size:12px;color:#64748b;margin-top:20px">If you did not request this, you can safely ignore this email.</p>
        <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0"/>
        <p style="font-size:11px;color:#94a3b8">FinSense Security Team • This is an automated message, please do not reply.</p>
      </div>
    </div>
    """

    res = await _send_email(email, subject, html)
    if not res.get("ok"):
        raise RuntimeError(res.get("error", "Failed to deliver password reset email"))
    return res

async def send_login_notification(
    email: str,
    name: str,
    user_agent: str = "",
    browser: str = "Unknown",
    os_name: str = "Unknown",
    device: str = "Desktop"
):
    """Send security alert notification when new device logs in."""
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    subject = "FinSense – Successful Login Detected"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#f8fafc;padding:24px;border-radius:12px;border:1px solid #e2e8f0">
      <h2 style="color:#0ea5e9">FinSense – Successful Login Detected</h2>
      <p>Hello {name},</p>
      <p>Your FinSense account was successfully logged into.</p>
      <ul>
        <li>Date: {date_str}</li>
        <li>Time: {time_str}</li>
        <li>Device: {device}</li>
        <li>Browser: {browser}</li>
        <li>Operating System: {os_name}</li>
      </ul>
      <p>If this was you, no action is required.</p>
      <p>If you do not recognize this activity, please secure your account immediately.</p>
      <p>Regards,<br>FinSense Security Team</p>
    </div>
    """

    return await _send_email(email, subject, html)

async def send_generic_email(to: str, subject: str, html: str):
    """Send arbitrary HTML email."""
    return await _send_email(to, subject, html)

async def send_test_email(to_email: str):
    """Send test diagnostic email to confirm active provider works."""
    provider = _get_active_provider().upper()
    subject = f"FinSense Email Test ({provider})"
    html = f"""
    <div style="font-family:Arial,sans-serif;padding:24px;border:1px solid #e2e8f0;border-radius:12px">
      <h2>FinSense Email Test</h2>
      <p>This is a test email sent from FinSense.</p>
      <p><strong>Active Provider:</strong> {provider}</p>
      <p><strong>Sender Address:</strong> {_email_from()}</p>
      <p><strong>Time:</strong> {datetime.utcnow().isoformat()} UTC</p>
      <p>If you received this message, your production email delivery is functioning properly.</p>
    </div>
    """
    res = await _send_email(to_email, subject, html)
    if not res.get("ok"):
        raise RuntimeError(res.get("error", "Failed to deliver test email"))
    return res
