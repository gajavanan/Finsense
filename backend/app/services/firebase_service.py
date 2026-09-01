import os
import logging
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_initialized = False

def get_firebase_app():
    """
    Safely initialize and return the Firebase Admin SDK App singleton.
    Supports environment variables (Render / Vercel):
      - FIREBASE_PROJECT_ID
      - FIREBASE_CLIENT_EMAIL
      - FIREBASE_PRIVATE_KEY (unescapes literal '\\n' characters)
    Also supports local credential file fallback if FIREBASE_CREDENTIALS_PATH is set.
    """
    global _firebase_initialized

    if _firebase_initialized and firebase_admin._apps:
        try:
            return firebase_admin.get_app()
        except ValueError:
            pass

    # 1. Environment Variable Certificate (Production / Render)
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", None) or os.getenv("FIREBASE_PROJECT_ID")
    client_email = getattr(settings, "FIREBASE_CLIENT_EMAIL", None) or os.getenv("FIREBASE_CLIENT_EMAIL")
    raw_private_key = getattr(settings, "FIREBASE_PRIVATE_KEY", None) or os.getenv("FIREBASE_PRIVATE_KEY")

    if project_id and client_email and raw_private_key:
        private_key = raw_private_key.replace("\\n", "\n").strip()
        cert_dict = {
            "type": "service_account",
            "project_id": project_id.strip(),
            "private_key": private_key,
            "client_email": client_email.strip(),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        try:
            cred = credentials.Certificate(cert_dict)
            app = firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info(f"[FIREBASE] Initialized Firebase Admin SDK for project {project_id}")
            return app
        except Exception as e:
            logger.error(f"[FIREBASE] Failed to initialize Firebase Admin credentials: {e}")
            raise RuntimeError("Invalid Firebase service account credentials.")

    # 2. File path fallback for local development (if serviceAccountKey.json is provided)
    cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None) or os.getenv("FIREBASE_CREDENTIALS_PATH")
    if cred_path and os.path.isfile(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info(f"[FIREBASE] Initialized Firebase Admin SDK from file {cred_path}")
            return app
        except Exception as e:
            logger.error(f"[FIREBASE] Failed to initialize Firebase Admin from file: {e}")
            raise RuntimeError("Invalid Firebase credentials file.")

    # 3. Development / Test environment warning
    if settings.APP_ENV != "production":
        logger.warning(
            "[FIREBASE] Credentials not configured. In development/testing, Firebase Admin is uninitialized."
        )
        return None

    raise RuntimeError("Firebase Admin service account credentials are required in production.")

def verify_firebase_phone_token(id_token: str) -> str:
    """
    Verify Firebase ID token and extract the verified phone number.
    Returns:
        Normalized E.164 phone number string (e.g. '+919876543210')
    Raises:
        ValueError: for invalid tokens, expired tokens, or tokens missing a verified phone claim.
        RuntimeError: if Firebase service is unavailable or unconfigured.
    """
    if not id_token or not isinstance(id_token, str) or not id_token.strip():
        raise ValueError("Firebase ID token is required.")

    app = get_firebase_app()
    if app is None:
        if settings.APP_ENV != "production":
            raise ValueError("Firebase Admin SDK is not configured in this development environment.")
        raise RuntimeError("Firebase service unavailable.")

    try:
        decoded_token: Dict[str, Any] = auth.verify_id_token(id_token.strip(), app=app)
    except auth.ExpiredIdTokenError:
        raise ValueError("Firebase verification token has expired. Please verify your phone number again.")
    except auth.RevokedIdTokenError:
        raise ValueError("Firebase verification token has been revoked. Please verify again.")
    except auth.InvalidIdTokenError:
        raise ValueError("Invalid Firebase verification token.")
    except Exception as e:
        logger.error(f"[FIREBASE] Token verification error: {type(e).__name__}")
        raise ValueError("Unable to verify Firebase phone token. Please try again.")

    phone_number = decoded_token.get("phone_number")
    if not phone_number or not isinstance(phone_number, str) or not phone_number.strip():
        raise ValueError("Firebase token does not contain a verified mobile phone number.")

    return phone_number.strip()
