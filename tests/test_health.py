from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_register_validation():
    # Test that invalid email is rejected
    response = client.post("/auth/register", json={
        "name": "Test",
        "email": "notanemail",
        "password": "Test@1234",
        "base_currency": "USD"
    })
    assert response.status_code == 422

def test_login_wrong_password():
    response = client.post("/auth/login", json={
        "email": "test@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401