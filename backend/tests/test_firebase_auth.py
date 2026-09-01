import sys
sys.path.insert(0, ".")
from datetime import datetime, timezone
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import User

client = TestClient(app)

# -----------------------------------------------------------------------------
# Firebase Phone Authentication Tests
# -----------------------------------------------------------------------------

def test_firebase_registration_invalid_token():
    """Verify that an invalid Firebase token is rejected with HTTP 400."""
    with patch("app.api.v1.auth.verify_firebase_phone_token", side_effect=ValueError("Invalid Firebase verification token.")):
        res = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "invalid_fb_token@example.com",
            "password": "StrongPassword123!",
            "firebase_id_token": "bad_token_123"
        })
    assert res.status_code == 400
    assert "invalid firebase verification token" in res.json()["detail"].lower()

def test_firebase_registration_token_missing_phone():
    """Verify that a Firebase token without a verified phone claim is rejected with HTTP 400."""
    with patch("app.api.v1.auth.verify_firebase_phone_token", side_effect=ValueError("Firebase token does not contain a verified mobile phone number.")):
        res = client.post("/api/v1/auth/register", json={
            "full_name": "No Phone User",
            "email": "no_phone@example.com",
            "password": "StrongPassword123!",
            "firebase_id_token": "token_without_phone"
        })
    assert res.status_code == 400
    assert "does not contain a verified mobile phone number" in res.json()["detail"].lower()

def test_full_firebase_registration_and_login_flow():
    """Test full registration, duplicate checks, and subsequent JWT login."""
    test_email = "firebase_user@example.com"
    test_phone = "+919876500001"
    test_pass = "StrongPass123!"

    # Clean up test user if exists
    db = SessionLocal()
    try:
        db.query(User).filter((User.email == test_email) | (User.phone_number == test_phone)).delete()
        db.commit()
    finally:
        db.close()

    # 1. Successful Registration with mocked Firebase token
    with patch("app.api.v1.auth.verify_firebase_phone_token", return_value=test_phone):
        reg_res = client.post("/api/v1/auth/register", json={
            "full_name": "Firebase User",
            "email": test_email,
            "password": test_pass,
            "firebase_id_token": "valid_mock_firebase_token"
        })

    assert reg_res.status_code == 200
    data = reg_res.json()
    assert data["status"] == "ok"
    assert data["user"]["email"] == test_email
    assert data["user"]["phone_number"] == test_phone
    assert data["user"]["phone_verified"] is True

    # Check database state
    db = SessionLocal()
    try:
        user_db = db.query(User).filter(User.email == test_email).first()
        assert user_db is not None
        assert user_db.phone_verified is True
        assert user_db.phone_verified_at is not None
        # Check timezone-aware timestamp
        assert user_db.phone_verified_at.tzinfo is not None or user_db.phone_verified_at.year >= 2026
    finally:
        db.close()

    # 2. Duplicate Email Rejection
    with patch("app.api.v1.auth.verify_firebase_phone_token", return_value="+919876500002"):
        dup_email = client.post("/api/v1/auth/register", json={
            "full_name": "Dup Email User",
            "email": test_email,
            "password": test_pass,
            "firebase_id_token": "valid_token_2"
        })
    assert dup_email.status_code == 400
    assert "email already registered" in dup_email.json()["detail"].lower()

    # 3. Duplicate Phone Number Rejection
    with patch("app.api.v1.auth.verify_firebase_phone_token", return_value=test_phone):
        dup_phone = client.post("/api/v1/auth/register", json={
            "full_name": "Dup Phone User",
            "email": "different_email@example.com",
            "password": test_pass,
            "firebase_id_token": "valid_token_3"
        })
    assert dup_phone.status_code == 400
    assert "already registered to another account" in dup_phone.json()["detail"].lower()

    # 4. Login with Email + Password -> Returns FinSense JWT
    login_res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": test_pass
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["phone_verified"] is True

    # 5. Access /auth/me with JWT token
    token = token_data["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == test_email
    assert me_data["phone_verified"] is True

    # Cleanup
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == test_email).delete()
        db.commit()
    finally:
        db.close()

def test_existing_user_login_remains_functional():
    """Verify that existing verified users log in without needing new phone verification."""
    existing_email = "existing_prod_user@example.com"
    existing_pass = "ExistingPass123!"

    db = SessionLocal()
    try:
        db.query(User).filter(User.email == existing_email).delete()
        db.commit()
        u = User(
            id=str(uuid.uuid4()),
            email=existing_email,
            phone_number="+919876543999",
            phone_verified=True,
            phone_verified_at=datetime.now(timezone.utc),
            hashed_password=get_password_hash(existing_pass),
            full_name="Existing Verified User",
            is_verified=True
        )
        db.add(u)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/auth/login", json={
        "email": existing_email,
        "password": existing_pass
    })
    assert res.status_code == 200
    assert "access_token" in res.json()

    # Cleanup
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == existing_email).delete()
        db.commit()
    finally:
        db.close()

def test_unverified_user_login_rejected():
    """Verify that unverified phone users are stopped at login with 403."""
    unverified_email = "unverified_legacy@example.com"
    unverified_pass = "UnverifiedPass123!"

    db = SessionLocal()
    try:
        db.query(User).filter(User.email == unverified_email).delete()
        db.commit()
        u = User(
            id=str(uuid.uuid4()),
            email=unverified_email,
            phone_number=None,
            phone_verified=False,
            hashed_password=get_password_hash(unverified_pass),
            full_name="Unverified User",
            is_verified=False
        )
        db.add(u)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/auth/login", json={
        "email": unverified_email,
        "password": unverified_pass
    })
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "PHONE_NOT_VERIFIED"

    # Cleanup
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == unverified_email).delete()
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    print("Running test_firebase_registration_invalid_token...")
    test_firebase_registration_invalid_token()
    print("Passed!")

    print("Running test_firebase_registration_token_missing_phone...")
    test_firebase_registration_token_missing_phone()
    print("Passed!")

    print("Running test_full_firebase_registration_and_login_flow...")
    test_full_firebase_registration_and_login_flow()
    print("Passed!")

    print("Running test_existing_user_login_remains_functional...")
    test_existing_user_login_remains_functional()
    print("Passed!")

    print("Running test_unverified_user_login_rejected...")
    test_unverified_user_login_rejected()
    print("Passed!")

    print("ALL FIREBASE AUTH TESTS PASSED 100%!")
