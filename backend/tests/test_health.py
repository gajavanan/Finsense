import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert "status" in r.json()

if __name__ == "__main__":
    test_root()
    test_health()
    print("Health tests passed!")
