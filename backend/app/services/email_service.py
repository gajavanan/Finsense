import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)

def _smtp_from() -> str:
    # For Gmail SMTP, MUST use authenticated user as sender; do not use noreply@finsense.app
    return settings.SMTP_FROM or settings.SMTP_USER or settings.EMAIL_FROM

def _email_provider() -> str:
    return (getattr(settings, "EMAIL_PROVIDER", "auto") or "auto").lower()

def _should_use_smtp() -> bool:
    provider = _email_provider()
    if provider == "smtp":
        return _smtp_configured()
    if provider == "resend":
        return False
    # auto: prefer SMTP when configured
    return _smtp_configured()

def _should_use_resend() -> bool:
    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY == "dummy":
        return False
    provider = _email_provider()
    if provider == "smtp":
        # Explicit SMTP in dev: ignore dummy Resend key
        return False
    return True

def _log_safe(action: str, recipient: str, success: bool, error: str = ""):
    # NEVER log password, token, JWT
    status = "successful" if success else f"failed: {error}"
    logger.info(f"[EMAIL] {action} | Recipient: {recipient} | SMTP configured: {_smtp_configured()} | SMTP connection: {status}")
    print(f"[EMAIL] {action} | Recipient: {recipient} | SMTP configured: {_smtp_configured()} | Email sent: {success} {error}")

def _send_smtp(to_email: str, subject: str, html: str, text_fallback: str = "") -> dict:
    """Send via real SMTP (Gmail: smtp.gmail.com:587 TLS). Returns {ok:bool, error:str}"""
    if not _smtp_configured():
        _log_safe(subject, to_email, False, "SMTP not configured - set SMTP_HOST/USER/PASSWORD")
        return {"ok": False, "error": "SMTP not configured"}

    from_addr = _smtp_from()
    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    # plain fallback
    if not text_fallback:
        # strip html tags roughly
        import re
        text_fallback = re.sub(r"<[^>]+>", "", html)
    msg.attach(MIMEText(text_fallback, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        # detailed connection logs without exposing password
        print(f"[EMAIL] SMTP connecting to {settings.SMTP_HOST}:{settings.SMTP_PORT} TLS={settings.SMTP_TLS} user={settings.SMTP_USER}")
        if settings.SMTP_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15, context=ssl.create_default_context()) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(from_addr, [to_email], msg.as_string())
        _log_safe(subject, to_email, True)
        return {"ok": True}
    except smtplib.SMTPAuthenticationError as e:
        err = f"SMTP authentication failed: {e.smtp_code} {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e.smtp_error}"
        _log_safe(subject, to_email, False, err)
        logger.error(err)
        return {"ok": False, "error": err}
    except smtplib.SMTPConnectError as e:
        err = f"SMTP connection failed: {e}"
        _log_safe(subject, to_email, False, err)
        return {"ok": False, "error": err}
    except Exception as e:
        err = f"SMTP error: {type(e).__name__}: {e}"
        # classify common cases
        msg_lower = str(e).lower()
        if "timeout" in msg_lower:
            err = f"Connection timeout: {e}"
        elif "tls" in msg_lower or "ssl" in msg_lower:
            err = f"TLS error: {e}"
        elif "sender" in msg_lower or "from" in msg_lower:
            err = f"Invalid sender: {e}"
        _log_safe(subject, to_email, False, err)
        logger.error(err)
        return {"ok": False, "error": err}

async def send_login_notification(email: str, name: str, user_agent: str = "", browser: str = "Unknown", os_name: str = "Unknown", device: str = "Desktop"):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    subject = "FinSense – Successful Login Detected"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#f8fafc;padding:24px;border-radius:12px">
      <h2 style="color:#0ea5e9">FinSense – Successful Login Detected</h2>
      <p>Hello {name},</p>
      <p>Your FinSense account was successfully logged in.</p>
      <ul>
        <li>Date: {date_str}</li>
        <li>Time: {time_str}</li>
        <li>Device: {device}</li>
        <li>Browser: {browser}</li>
        <li>Operating System: {os_name}</li>
      </ul>
      <p>If this was you, no action is required.</p>
      <p>If you do not recognize this activity, please secure your account.</p>
      <p>Regards,<br>FinSense Security Team</p>
    </div>
    """
    # Explicit provider selection: EMAIL_PROVIDER=smtp ignores Resend dummy
    print(f"[EMAIL] Provider: {_email_provider()} | SMTP configured: {_smtp_configured()} | Resend configured: {_should_use_resend()}")
    if _should_use_smtp():
        res = _send_smtp(email, subject, html)
        return {"smtp": res}
    if _should_use_resend():
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            r = resend.Emails.send({"from": settings.EMAIL_FROM, "to": [email], "subject": subject, "html": html})
            _log_safe(subject, email, True)
            return r
        except Exception as e:
            _log_safe(subject, email, False, str(e))
            return {"error": str(e)}
    _log_safe(subject, email, False, "No email provider configured - set SMTP or RESEND_API_KEY")
    return {"mock": True, "error": "No provider"}

async def send_verification_email(email: str, name: str, token: str):
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your FinSense account"
    # Professional HTML email per spec
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden">
      <div style="background:linear-gradient(135deg,#0ea5e9,#7c3aed);padding:24px;text-align:center;color:white">
        <div style="background:white;color:#0ea5e9;width:40px;height:40px;border-radius:10px;display:inline-grid;place-items:center;font-weight:bold">●</div>
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
    print(f"[EMAIL VERIFICATION] Recipient: {email} | Provider: {_email_provider()} | SMTP configured: {_smtp_configured()} | FRONTEND_URL: {settings.FRONTEND_URL}")

    if _should_use_smtp():
        res = _send_smtp(email, subject, html)
        if res.get("ok"):
            print(f"[EMAIL VERIFICATION] Email sent: true to {email}")
            return {"ok": True}
        else:
            print(f"[EMAIL VERIFICATION] Email sent: false error={res.get('error')}")
            # Do not swallow - raise so caller can log
            raise Exception(res.get("error"))

    if _should_use_resend():
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            r = resend.Emails.send({"from": settings.EMAIL_FROM, "to": [email], "subject": subject, "html": html})
            print(f"[EMAIL VERIFICATION] Email sent: true via Resend to {email}")
            return r
        except Exception as e:
            print(f"[EMAIL VERIFICATION] Resend failed: {e}")
            raise

    # No provider configured - log clearly, do not expose token
    print(f"[EMAIL VERIFICATION] SMTP not configured - set SMTP_HOST=smtp.gmail.com SMTP_PORT=587 SMTP_USER/SMTP_PASSWORD (App Password) to send real email. Verification link would be {link} but not logged with token.")
    _log_safe(subject, email, False, "SMTP not configured")
    raise Exception("SMTP not configured - set SMTP_HOST/SMTP_USER/SMTP_PASSWORD in backend/.env")

async def send_password_reset_email(email: str, name: str, token: str):
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "FinSense – Password Reset"
    html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px"><h2>Password Reset</h2><p>Hello {name},</p><p>Click <a href='{link}'>here</a> to reset password. Link expires in 1 hour.</p><p>{link}</p></div>"""
    if _should_use_smtp():
        res = _send_smtp(email, subject, html)
        if res.get("ok"):
            return {"ok": True}
        raise Exception(res.get("error"))
    if _should_use_resend():
        import resend
        resend.api_key = settings.RESEND_API_KEY
        return resend.Emails.send({"from": settings.EMAIL_FROM, "to": [email], "subject": subject, "html": html})
    _log_safe(subject, email, False, "No provider")
    return {"mock": True}

async def send_generic_email(to: str, subject: str, html: str):
    if _should_use_smtp():
        res = _send_smtp(to, subject, html)
        return {"ok": res.get("ok"), "error": res.get("error")}
    if _should_use_resend():
        import resend
        resend.api_key = settings.RESEND_API_KEY
        return resend.Emails.send({"from": settings.EMAIL_FROM, "to": [to], "subject": subject, "html": html})
    _log_safe(subject, to, False, "No provider")
    return {"mock": True}

async def send_test_email(to_email: str):
    subject = "FinSense SMTP Test"
    html = f"""
    <div style="font-family:Arial,sans-serif;padding:24px">
      <h2>FinSense SMTP Test</h2>
      <p>This is a test email from FinSense.</p>
      <p>SMTP_HOST: {settings.SMTP_HOST}</p>
      <p>Time: {datetime.utcnow().isoformat()} UTC</p>
      <p>If you received this, SMTP is working correctly.</p>
    </div>
    """
    print(f"[EMAIL TEST] Recipient: {to_email} | Provider: {_email_provider()} | SMTP configured: {_smtp_configured()}")
    if _should_use_smtp():
        res = _send_smtp(to_email, subject, html)
        if not res.get("ok"):
            raise Exception(res.get("error"))
        return {"ok": True}
    if _should_use_resend():
        import resend
        resend.api_key = settings.RESEND_API_KEY
        r = resend.Emails.send({"from": settings.EMAIL_FROM, "to": [to_email], "subject": subject, "html": html})
        return {"ok": True, "resend": r}
    raise Exception("SMTP not configured - cannot send test email. Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD")
