from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import  engine, Base, SessionLocal
from app.models import *
from app.routers import auth ,categories, expenses,budgets,groups,reports
from app.core.seed import seed_categories

Base.metadata.create_all(bind=engine)

# Seed system categories on startup
db = SessionLocal()
try:
    seed_categories(db)
finally:
    db.close()


app = FastAPI(
    title="Expense Tracker API",
    description="Personal and team expense tracking with multi-currency support",
    version="1.0.0"
)

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


@app.get("/health")
def health_check():
    return {"status": "ok"}