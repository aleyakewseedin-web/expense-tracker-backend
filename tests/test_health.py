from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ── HEALTH ──
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# ── AUTH ──
def test_register_validation_invalid_email():
    response = client.post("/auth/register", json={
        "name": "Test",
        "email": "notanemail",
        "password": "Test@1234",
        "base_currency": "USD"
    })
    assert response.status_code == 422

def test_register_validation_weak_password():
    response = client.post("/auth/register", json={
        "name": "Test",
        "email": "test@test.com",
        "password": "weak",
        "base_currency": "USD"
    })
    assert response.status_code == 422

def test_login_wrong_password():
    response = client.post("/auth/login", json={
        "email": "test@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_login_nonexistent_user():
    response = client.post("/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "Test@1234"
    })
    assert response.status_code == 401

def test_get_me_without_token():
    response = client.get("/auth/me")
    assert response.status_code == 403

# ── CATEGORIES ──
def test_get_categories_without_token():
    response = client.get("/categories")
    assert response.status_code == 403

# ── EXPENSES ──
def test_get_expenses_without_token():
    response = client.get("/expenses")
    assert response.status_code == 403

def test_create_expense_without_token():
    response = client.post("/expenses", json={
        "original_amount": 100,
        "currency_code": "USD",
        "category_id": "00000000-0000-0000-0000-000000000000",
        "expense_date": "2026-01-01"
    })
    assert response.status_code == 403

def test_create_expense_future_date():
    # First register and login to get token
    client.post("/auth/register", json={
        "name": "Test User",
        "email": "testfuture@test.com",
        "password": "Test@1234!",
        "base_currency": "USD"
    })
    login_res = client.post("/auth/login", json={
        "email": "testfuture@test.com",
        "password": "Test@1234!"
    })
    token = login_res.json().get("access_token")
    
    response = client.post("/expenses", 
        json={
            "original_amount": 100,
            "currency_code": "USD",
            "category_id": "00000000-0000-0000-0000-000000000000",
            "expense_date": "2099-01-01"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422

# ── BUDGETS ──
def test_get_budgets_without_token():
    response = client.get("/budgets?month=2026-05")
    assert response.status_code == 403

def test_create_budget_negative_amount():
    client.post("/auth/register", json={
        "name": "Budget Test",
        "email": "budgettest@test.com",
        "password": "Test@1234!",
        "base_currency": "USD"
    })
    login_res = client.post("/auth/login", json={
        "email": "budgettest@test.com",
        "password": "Test@1234!"
    })
    token = login_res.json().get("access_token")

    response = client.post("/budgets",
        json={
            "category_id": "00000000-0000-0000-0000-000000000000",
            "month": 6,
            "year": 2026,
            "budget_amount_usd": -100
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422

# ── GROUPS ──
def test_get_groups_without_token():
    response = client.get("/groups")
    assert response.status_code == 403

def test_create_group_without_token():
    response = client.post("/groups", json={"name": "Test Group"})
    assert response.status_code == 403

# ── REPORTS ──
def test_get_report_without_token():
    response = client.get("/reports/monthly?month=2026-05")
    assert response.status_code == 403

def test_get_report_invalid_month():
    client.post("/auth/register", json={
        "name": "Report Test",
        "email": "reporttest@test.com",
        "password": "Test@1234!",
        "base_currency": "USD"
    })
    login_res = client.post("/auth/login", json={
        "email": "reporttest@test.com",
        "password": "Test@1234!"
    })
    token = login_res.json().get("access_token")

    response = client.get("/reports/monthly?month=invalid",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400