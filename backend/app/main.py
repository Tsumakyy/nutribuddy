from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import Base, engine
from . import models  # noqa: F401
from .models import MEAL_KEYS
from .routers import auth, patients, diets, checkins, metrics, buddy, foods

app = FastAPI(title="NutriBuddy API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def _sync_mysql_meal_key_enum() -> None:
    if engine.dialect.name != "mysql":
        return
    enum_values = ", ".join(f"'{key}'" for key in MEAL_KEYS)
    with engine.begin() as conn:
        for table in ("diet_items", "diet_overrides", "checkins", "meal_configs"):
            conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN meal_key ENUM({enum_values}) NOT NULL"))


_sync_mysql_meal_key_enum()

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(diets.router)
app.include_router(checkins.router)
app.include_router(metrics.router)
app.include_router(buddy.router)
app.include_router(foods.router)

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}