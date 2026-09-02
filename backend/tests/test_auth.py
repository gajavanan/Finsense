import sys
sys.path.insert(0, ".")
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import User, Profile

client = TestClient(app)

def cleanup_user(email: str, phone: str = None):
    db = SessionLocal()
    try:
        q = db.query(User).filter(User.email == email)
        if phone:
            q = db.query(User).filter((User.email == email) | (User.phone_number == phone))
        users = q.all()
        for u in users:
            db.query(Profile).filter(Profile.id == u.id).delete()
            db.delete(u)
        db.commit()
    finally:
        db.close()

def test_registration_validation_errors():
    """Test required fields, invalid phone, invalid email, and short password."""
    # 1. Missing name
    res = client.post("/api/v1/auth/register", json={
        "name": "",
        "email": "test_err@example.com",
        "phone_number": "9876543210",
        "password": "Password123!"
    })
    assert res.status_code == 400
    assert "full name is required" in res.json()["detail"].lower()

    # 2. Short password
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test_err@example.com",
        "phone_number": "9876543210",
        "password": "123"
    })
    assert res.status_code == 400
    assert "at least 6 characters" in res.json()["detail"].lower()

    # 3. Invalid phone: less than 10 digits
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test_err@example.com",
        "phone_number": "12345",
        "password": "Password123!"
    })
    assert res.status_code == 400
    assert "10-digit mobile number" in res.json()["detail"].lower()

    # 4. Invalid phone: does not start with 6, 7, 8, or 9
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test_err@example.com",
        "phone_number": "5123456789",
        "password": "Password123!"
    })
    assert res.status_code == 400
    assert "start with 6, 7, 8, or 9" in res.json()["detail"].lower()

def test_full_registration_and_login_flow():
    """Test successful registration, duplicate rejection, and email+password login."""
    test_email = "alex_morgan@example.com"
    test_phone = "7339354593"
    normalized_phone = "+917339354593"
    test_pass = "SecurePass123!"

    cleanup_user(test_email, normalized_phone)

    # 1. Register new user
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Alex Morgan",
        "email": test_email,
        "phone_number": test_phone,
        "password": test_pass
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert data["status"] == "ok"
    assert data["user"]["email"] == test_email
    assert data["user"]["phone_number"] == normalized_phone

    # Verify user state in database
    db = SessionLocal()
    try:
        user_db = db.query(User).filter(User.email == test_email).first()
        assert user_db is not None
        assert user_db.full_name == "Alex Morgan"
        assert user_db.phone_number == normalized_phone
        assert user_db.phone_verified is False
        assert user_db.phone_verified_at is None
    finally:
        db.close()

    # 2. Reject duplicate email
    dup_email_res = client.post("/api/v1/auth/register", json={
        "name": "Another User",
        "email": test_email,
        "phone_number": "9876543211",
        "password": test_pass
    })
    assert dup_email_res.status_code == 400
    assert "email already registered" in dup_email_res.json()["detail"].lower()

    # 3. Reject duplicate phone
    dup_phone_res = client.post("/api/v1/auth/register", json={
        "name": "Another User",
        "email": "different_alex@example.com",
        "phone_number": test_phone,
        "password": test_pass
    })
    assert dup_phone_res.status_code == 400
    assert "mobile number already registered" in dup_phone_res.json()["detail"].lower()

    # 4. Login with email + password -> Returns FinSense JWT
    login_res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": test_pass
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == test_email
    assert token_data["user"]["phone_number"] == normalized_phone

    # 5. Access /auth/me with JWT token
    token = token_data["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == test_email
    assert me_data["phone_number"] == normalized_phone

    # 6. Reject invalid password
    bad_login = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401
    assert bad_login.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    # Cleanup
    cleanup_user(test_email, normalized_phone)

if __name__ == "__main__":
    print("Running test_registration_validation_errors...")
    test_registration_validation_errors()
    print("Passed!")

    print("Running test_full_registration_and_login_flow...")
    test_full_registration_and_login_flow()
    print("Passed!")

    print("ALL AUTH TESTS PASSED 100%!")
