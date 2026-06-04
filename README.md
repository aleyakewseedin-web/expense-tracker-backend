# 💸 Expense Tracker — Multi-Currency Personal & Group Expense Manager

A full-stack expense tracking application built with FastAPI, PostgreSQL, and Redis. Features AI-powered monthly financial insights, multi-currency support, group expense splitting, and JWT authentication with 2FA.

---

## 🌐 Live URLs

| Service | URL |
|---|---|
| Frontend | https://expense-tracker-frontend-wbpa.onrender.com |
| Backend API | https://expense-tracker-backend-zskj.onrender.com |
| API Docs (Swagger) | https://expense-tracker-backend-zskj.onrender.com/docs |

---

## 📁 Repositories

| Repo | URL |
|---|---|
| Backend | https://github.com/aleyakewseedin-web/expense-tracker-backend |
| Frontend | https://github.com/aleyakewseedin-web/expense-tracker-frontend |

---

## ✨ Features

- **Expense Logging** — Log expenses in any currency, automatically converted to USD at the daily exchange rate
- **Budget Tracking** — Set monthly per-category budgets with visual progress bars and over-budget alerts
- **AI Monthly Report** — Llama 3 (via Groq) generates natural language financial insights, cached in Redis
- **Group Expenses** — Create groups, add members, split bills equally, by percentage, or exact amounts
- **Multi-Currency** — 31 supported currencies via Frankfurter API, rates frozen at ingestion time
- **JWT Authentication** — Secure token-based auth with automatic session expiry
- **2FA Security** — TOTP-based two-factor authentication via Google Authenticator
- **Dark & Light Mode** — Toggle between themes, preference saved in localStorage
- **Pagination** — Expenses paginated 5 per page

---

## 🛠 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI (Python) | Async, auto-generates /docs, Pydantic validation |
| Database | PostgreSQL | NUMERIC(12,2) precision, strong FK constraints |
| Cache | Redis | Sub-millisecond response for AI report cache |
| AI | Groq / Llama 3 | Free, fast AI inference for financial insights |
| Currency | Frankfurter API | Free exchange rates, no API key required |
| Auth | JWT + bcrypt | Stateless authentication, secure password hashing |
| 2FA | pyotp (TOTP) | Google Authenticator compatible |
| Containerization | Docker + Docker Compose | One command runs full stack |
| CI/CD | GitHub Actions | Runs test suite on every push to main |
| Deployment | Render | Free tier, Frankfurt region |

---

## 🗄 Database Schema

10 tables: `users`, `categories`, `expenses`, `budgets`, `groups`, `group_members`, `expense_splits`, `settlements`, `monthly_reports`, `currency_snapshots`

All primary keys use UUID. Financial values use `NUMERIC(12,2)` for precision.

---

## 🚀 Running Locally

### Prerequisites
- Python 3.11+
- Docker Desktop
- PostgreSQL (or use Docker)

### 1. Clone the repository
```bash
git clone https://github.com/aleyakewseedin-web/expense-tracker-backend.git
cd expense-tracker-backend
```

### 2. Create `.env` file
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/expense_tracker
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GROQ_API_KEY=your-groq-api-key
POSTGRES_PASSWORD=yourpassword
```

### 3. Run with Docker Compose
```bash
docker compose up --build
```

This starts PostgreSQL, Redis, and the FastAPI server together.

### 4. Run the frontend
```bash
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500`

### 5. Run locally without Docker
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 🧪 Running Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

16 tests covering health checks, auth validation, JWT protection, input validation, and rate limiting.

---

## 📐 Multi-Currency Strategy

Every expense stores two amounts:
- `original_amount` + `currency_code` — what the user entered
- `amount_usd` + `exchange_rate` — frozen at ingestion time

Exchange rates are fetched from Frankfurter API once per currency pair per day and cached in `currency_snapshots`. This ensures historical reports remain accurate regardless of future rate fluctuations.

---

## 🔐 Security

- All endpoints protected with JWT Bearer tokens
- Passwords hashed with bcrypt
- Optional TOTP-based 2FA (Google Authenticator)
- Rate limiting on all write endpoints (slowapi)
- Pydantic validation: positive amounts, valid ISO 4217 currencies, no future dates, split percentages sum to 100
- Group-level authorization: members can only access their own groups

---

## 📦 Project Structure

```
expense-tracker/
├── app/
│   ├── core/          # config, security, seed
│   ├── models/        # SQLAlchemy models
│   ├── routers/       # FastAPI route handlers
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # currency, cache, AI report
│   ├── database.py
│   ├── dependencies.py
│   └── main.py
├── tests/
│   └── test_health.py
├── frontend/
│   └── index.html
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 👤 Author

**Aleya Kewseedin**  
linkedin:https://www.linkedin.com/in/aleya-kewseedin-92349a3b1/
