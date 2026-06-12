from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import  engine, Base, SessionLocal
from app.models import *
from app.core.seed import seed_categories
from app.routers import auth, categories, expenses, budgets, groups, reports, twofa, receipts,analytics
Base.metadata.create_all(bind=engine)

# Seed system categories on startup
db = SessionLocal()
try:
    seed_categories(db)
finally:
    db.close()
# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Expense Tracker API",
    description="Personal and team expense tracking with multi-currency support",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(budgets.router)
app.include_router(groups.router)
app.include_router(reports.router)
app.include_router(twofa.router)
app.include_router(receipts.router)
app.include_router(analytics.router)

# Debug routes
for route in app.routes:
    print(f"ROUTE: {route.path}")
@app.get("/health")
def health_check():
    return {"status": "ok"}