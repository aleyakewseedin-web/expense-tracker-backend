from sqlalchemy.orm import Session
from app.models.category import Category

SYSTEM_CATEGORIES = [
    "Food", "Transport", "Housing", "Entertainment",
    "Health", "Utilities", "Education", "Shopping", "Travel", "Other"
]

def seed_categories(db: Session):
    for name in SYSTEM_CATEGORIES:
        exists = db.query(Category).filter(
            Category.name == name,
            Category.is_system == True
        ).first()
        if not exists:
            db.add(Category(name=name, is_system=True, user_id=None))
    db.commit()